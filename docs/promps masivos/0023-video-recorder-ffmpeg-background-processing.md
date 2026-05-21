# 0023 — Grabación de Video In-App, Compresión FFmpeg Async y Barra de Progreso

## Objetivo

Reemplazar el flujo de captura de video basado en `<input capture="environment">` (que delega al sistema operativo y puede guardar en galería) por un grabador in-app construido sobre `MediaRecorder` que:

1. Captura el video directamente dentro de la app, sin persistir nada en el dispositivo.
2. Sube el archivo crudo al backend con una barra de progreso HTTP real (bytes transferidos, 0→100 %).
3. Comprime el video en backend con **FFmpeg vía `subprocess.run`** corriendo en un **`BackgroundTask` de FastAPI**, devolviendo la respuesta inmediatamente y actualizando un registro de estado (`uploaded → processing → ready | failed`).
4. Muestra en el frontend el progreso de subida (fase HTTP) seguido del estado de procesamiento (fase FFmpeg), mediante polling al nuevo endpoint `GET /api/media/{media_id}/status`.
5. Funciona correctamente (con fallback de codec) en Android de gama baja.
6. Mantiene el selector de galería como alternativa al grabador in-app.

Contextos afectados: **Tareas**, **Tickets**, **Formulario de satisfacción (público)**.

---

## Decisiones de diseño

| Decisión | Valor |
|---|---|
| Ejecución de FFmpeg | Background task (FastAPI `BackgroundTasks`), sin bloquear el request |
| Abstracción de cola | `VideoProcessingPort` Protocol — swap a RQ/Celery sin tocar endpoints |
| Herramienta FFmpeg | `subprocess.run([...], shell=False)` — sin `ffmpeg-python` |
| Stderr de FFmpeg | Logueado en `ERROR` si `returncode != 0` |
| Codec de salida | `libx264 + aac`, `-movflags +faststart`, `-map_metadata -1` |
| Tabla de estado | Nueva tabla `video_processing_jobs` — no contamina `task_attachments` / `ticket_attachments` |
| `media_id` para polling | UUID de `video_processing_jobs`, devuelto en la respuesta del upload |
| Progreso de subida | HTTP bytes únicamente (0–100 %); `Procesando video...` es fase separada |
| Polling del estado | Cada 2 s hasta `ready` o `failed` |
| Thumbnail | Campo reservado en esquema, siempre `null` en MVP |
| Galería como fallback | `<input type="file" accept="video/*">` sin `capture` (abre galería, no cámara) |
| Liberación de cámara | `stream.getTracks().forEach(t => t.stop())` en **todo** path: stop, cancel, error, `ngOnDestroy` |
| Límite de duración | Frontend auto-detiene en `VIDEO_MAX_DURATION_SECONDS`; backend valida con `ffprobe` |
| Duración por defecto | `VIDEO_MAX_DURATION_SECONDS=30` |
| Fallback de codec Android | `vp9,opus` → `vp8,opus` → `webm` → `mp4` → error informativo inline |

---

## Variables de entorno nuevas

Todas en `microtv-crm-backend/.env` y leídas en `config.py`:

| Variable | Default | Descripción |
|---|---|---|
| `VIDEO_MAX_DURATION_SECONDS` | `30` | Límite de duración validado con ffprobe en backend y auto-stop en frontend |
| `VIDEO_MAX_UPLOAD_MB` | `80` | Tamaño máximo del archivo crudo subido |
| `VIDEO_TARGET_HEIGHT` | `720` | Altura de salida FFmpeg; ancho auto-escalado con `-2:` |
| `VIDEO_TARGET_FPS` | `24` | FPS de salida FFmpeg |
| `VIDEO_FFMPEG_CRF` | `28` | Factor de calidad H.264 (menor = mayor calidad/tamaño) |
| `VIDEO_FFMPEG_PRESET` | `veryfast` | Preset de velocidad de encoding FFmpeg |
| `VIDEO_ALLOWED_MIME_TYPES` | `video/mp4,video/webm,video/quicktime` | MIME types aceptados en upload |

Reemplaza a `TASK_VIDEOS_MAX_BYTES` para videos (queda para imágenes).

---

## Fase 1 — Backend: Migraciones de base de datos

> Las dos migraciones pueden trabajarse en paralelo.

### 1.1 Nueva tabla `video_processing_jobs` (Alembic)

```sql
CREATE TABLE video_processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR(20) NOT NULL DEFAULT 'uploaded',
    -- valores: uploaded | processing | ready | failed
    original_url  TEXT NOT NULL,
    original_path TEXT NOT NULL,
    optimized_url  TEXT,
    optimized_path TEXT,
    thumbnail_url  TEXT,  -- siempre NULL en MVP
    error          TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
```

### 1.2 FK en tablas de adjuntos (Alembic)

```sql
ALTER TABLE task_attachments
    ADD COLUMN video_job_id UUID REFERENCES video_processing_jobs(id);

ALTER TABLE ticket_attachments
    ADD COLUMN video_job_id UUID REFERENCES video_processing_jobs(id);

-- Satisfacción: agregar columna equivalente a la tabla de medios del formulario
```

---

## Fase 2 — Backend: Configuración

### 2.1 `src/crm_backend/core/config.py`

Agregar en `Settings`:

```python
video_max_duration_seconds: int = Field(default=30)
video_max_upload_mb: int = Field(default=80)
video_target_height: int = Field(default=720)
video_target_fps: int = Field(default=24)
video_ffmpeg_crf: int = Field(default=28)
video_ffmpeg_preset: str = Field(default="veryfast")
video_allowed_mime_types: Annotated[list[str], NoDecode] = Field(
    default_factory=lambda: ["video/mp4", "video/webm", "video/quicktime"]
)
```

---

## Fase 3 — Backend: VideoProcessor

### 3.1 `src/crm_backend/infrastructure/video_processor.py` (**nuevo**)

Clase `VideoProcessor`:

- **`get_duration_seconds(input_path: Path) -> float | None`**
  - Ejecuta: `subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(input_path)], shell=False, capture_output=True)`
  - Parsea `result.stdout` → `json.loads` → `float(data['format']['duration'])`
  - Retorna `None` en cualquier excepción (binario ausente, returncode != 0, parse error)

- **`compress(input_path: Path, output_path: Path, settings: Settings) -> None`**
  - Ejecuta:
    ```
    ffmpeg -y -i <input>
      -vf "scale=-2:<height>,fps=<fps>"
      -c:v libx264 -crf <crf> -preset <preset>
      -c:a aac
      -movflags +faststart
      -map_metadata -1
      <output>.mp4
    ```
  - `shell=False`, `capture_output=True`
  - Si `returncode != 0`: loguea `result.stderr.decode()` en `ERROR`, lanza `VideoProcessingError`

---

## Fase 4 — Backend: VideoJobRepository

### 4.1 `src/crm_backend/infrastructure/video_job_repository.py` (**nuevo**)

Clase `VideoJobRepository` (SQLAlchemy, inyectada con `Session`):

- `create(original_url: str, original_path: str) -> VideoJobRecord` — status=`uploaded`
- `update_status(job_id: UUID, status: str, optimized_url=None, optimized_path=None, error=None) -> None`
- `get_by_id(job_id: UUID) -> VideoJobRecord | None`

---

## Fase 5 — Backend: VideoProcessingService

### 5.1 `src/crm_backend/services/video_processing_service.py` (**nuevo**)

**`VideoProcessingPort` (Protocol):**

```python
class VideoProcessingPort(Protocol):
    def enqueue(
        self,
        job_id: UUID,
        input_path: Path,
        output_path: Path,
    ) -> None: ...
```

**`BackgroundTaskVideoProcessingService(VideoProcessingPort)`:**

- Constructor: recibe `BackgroundTasks`, `VideoProcessor`, `VideoJobRepository`, `Settings`
- `enqueue(...)` → `background_tasks.add_task(self._run, job_id, input_path, output_path)`
- `_run(job_id, input_path, output_path)`:
  1. `repo.update_status(job_id, 'processing')`
  2. `duration = processor.get_duration_seconds(input_path)` — si supera `VIDEO_MAX_DURATION_SECONDS`: `repo.update_status(job_id, 'failed', error='...')`, borra raw, retorna
  3. `processor.compress(input_path, output_path, settings)`
  4. Si OK: `repo.update_status(job_id, 'ready', optimized_url=..., optimized_path=...)`, borra raw
  5. Si `VideoProcessingError`: `repo.update_status(job_id, 'failed', error=str(exc))`, borra raw

> **Contrato de aislamiento**: migrar a RQ/Celery requiere sólo una nueva clase `RQVideoProcessingService(VideoProcessingPort)`. Los endpoints no cambian.

---

## Fase 6 — Backend: Cambios en endpoints de upload

### 6.1 `src/crm_backend/infrastructure/task_media_storage.py`

`VideoTaskMediaUploadStrategy`:

- Validar MIME contra `settings.video_allowed_mime_types` (no por extensión)
- Validar tamaño contra `settings.video_max_upload_mb * 1024 * 1024`
- Escribir bytes crudos en `tasks/videos/raw/{uuid}{ext}` (subdirectorio `raw/`)
- **Sin FFmpeg aquí** — sólo guardar + validar

### 6.2 `src/crm_backend/api/endpoints/tasks.py`

En `upload_task_attachments`:

1. Llamar a `strategy.store()` → `StoredTaskMedia` con ruta raw
2. `video_job = VideoJobRepository.create(original_url, original_path)`
3. `task_attachment.video_job_id = video_job.id`
4. `VideoProcessingService.enqueue(video_job.id, raw_path, output_path)`
5. Respuesta incluye `media_id: video_job.id` en el schema de `TaskAttachment`

### 6.3 `src/crm_backend/api/endpoints/tickets.py`

Mismo patrón que 6.2.

### 6.4 `src/crm_backend/services/satisfaction_form_service.py` + `public_tickets.py`

Mismo patrón para videos del formulario público de satisfacción.

---

## Fase 7 — Backend: Endpoint de estado

### 7.1 `src/crm_backend/api/endpoints/media.py` (**nuevo**)

```
GET /api/media/{media_id}/status
```

- Auth: JWT requerido (endpoint público de satisfacción puede omitir auth o usar token de sesión)
- Consulta `VideoJobRepository.get_by_id(media_id)`
- 404 si no existe
- Respuesta:

```json
{
  "id": "uuid",
  "status": "uploaded | processing | ready | failed",
  "original_url": "/media/tasks/videos/raw/abc.webm",
  "optimized_url": "/media/tasks/videos/abc.mp4",
  "thumbnail_url": null,
  "error": null
}
```

### 7.2 `src/crm_backend/api/router.py`

Registrar el nuevo router de `media.py`.

---

## Fase 8 — Frontend: Configuración de runtime

### 8.1 `src/app/core/config/crm-api.config.ts`

- Agregar a `CrmRuntimeConfig`: `videoMaxDurationSeconds?: number | string`, `videoMaxUploadMb?: number | string`
- Exponer en `crmMediaConfig.video`: `maxDurationSeconds` (default `30`), `maxUploadMb` (default `80`)

---

## Fase 9 — Frontend: VideoRecorderService

### 9.1 `src/app/core/services/video-recorder.service.ts` (**nuevo**)

- **`startRecording(previewEl: HTMLVideoElement): Observable<Blob>`**
  - `getUserMedia({ video: { facingMode: 'environment' }, audio: true })`
  - Asigna `stream` a `previewEl.srcObject`
  - Negociación de codec (orden de prioridad para Android de gama baja):
    1. `video/webm;codecs=vp9,opus`
    2. `video/webm;codecs=vp8,opus`
    3. `video/webm`
    4. `video/mp4`
    5. `UnsupportedRecordingFormatError` — muestra error inline, nunca crash
  - Acumula chunks en `ondataavailable`
  - Auto-detiene a los `videoMaxDurationSeconds` segundos
  - Al parar: `new Blob(chunks, { type: mimeType })` emitido por el Observable

- **`stopRecording(): void`** — detiene `MediaRecorder` y llama a `_cleanupTracks()`

- **`cancel(): void`** — igual a `stopRecording()` sin emitir Blob

- **`_cleanupTracks(): void`** — `this._stream?.getTracks().forEach(t => t.stop())`
  - Llamado en: `stopRecording()`, `cancel()`, manejador de error de `getUserMedia`, `ngOnDestroy()`

- Señales: `isRecording: Signal<boolean>`, `elapsedSeconds: Signal<number>`

---

## Fase 10 — Frontend: VideoRecorderComponent

### 10.1 `src/app/shared/ui/video-recorder/video-recorder.component.*` (**nuevo**)

Componente standalone con:

- `<video #preview autoplay muted playsinline>` — feed de cámara en vivo (nunca guardado)
- Botón **Grabar** / **Detener** (rojo, toggle)
- Contador de tiempo transcurrido / tiempo restante
- Botón **Cancelar** — llama a `service.cancel()`, emite `cancelled`
- Mensaje de error inline (permisos denegados, codec no soportado)

Outputs: `recordingComplete: EventEmitter<Blob>`, `cancelled: EventEmitter<void>`

`ngOnDestroy()` siempre llama a `service.stopRecording()` para limpiar tracks si el modal se cierra sin acción explícita.

---

## Fase 11 — Frontend: Progreso de subida + poller de estado

### 11.1 `src/app/core/services/task-management.service.ts`

`uploadTaskAttachments()`:
- Agregar `{ reportProgress: true, observe: 'events' }` al `HttpClient`
- Retorna `Observable<HttpEvent<TaskAttachmentResponse>>` (el response incluye `media_id`)

### 11.2 `src/app/core/services/ticket-management.service.ts`

Mismo cambio que 11.1.

### 11.3 `src/app/core/services/media-status-poller.service.ts` (**nuevo**)

- **`pollUntilDone(mediaId: string, intervalMs = 2000): Observable<MediaStatusResponse>`**
  - `interval(intervalMs)` → `switchMap` → `GET /api/media/{mediaId}/status`
  - Completa con `takeWhile((r) => r.status !== 'ready' && r.status !== 'failed', true)`

### 11.4 `src/app/shared/facades/media-upload.facade.ts`

- Agregar `uploadProgress: Signal<number | null>` — actualizado desde `HttpUploadProgressEvent` (`Math.round(loaded / total * 100)`)
- Agregar `mediaStatus: Signal<'uploading' | 'processing' | 'ready' | 'failed' | null>`
- Al recibir `HttpResponse`: cambiar `mediaStatus` a `'processing'`, iniciar `MediaStatusPollerService.pollUntilDone(media_id)` → actualiza `mediaStatus`

### 11.5 `src/app/shared/ui/upload-progress/upload-progress.component.*` (**nuevo**)

Inputs: `@Input() progress: number | null`, `@Input() status: string | null`

| Condición | UI |
|---|---|
| `progress < 100` | Barra de progreso con porcentaje |
| `progress === 100 && status === 'processing'` | Spinner + "Procesando video..." |
| `status === 'failed'` | Mensaje de error rojo |
| `status === 'ready'` | Componente oculto (el video ya se renderiza en el padre) |

---

## Fase 12 — Frontend: Integración en UIs de adjuntos

### 12.1 `src/app/shared/facades/media-upload/video-upload.strategy.ts`

- `supports(file)`: ya acepta `video/webm`, `video/mp4`, `video/quicktime`
- Agregar lógica de nombre fallback: si `file.name` está vacío → `recording-{Date.now()}.webm`

### 12.2 `src/app/features/tasks/components/task-attachments-section/*`

- Agregar botón **"Grabar video"** → abre `VideoRecorderComponent`
- `recordingComplete(blob)` → `new File([blob], 'recording-{Date.now()}.webm', { type: blob.type })` → `MediaUploadFacade.upload()`
- Conservar `<input type="file" accept="video/*">` sin atributo `capture` como **"Elegir de galería"**
- Eliminar `<input capture="environment" accept="video/*">` (reemplazado por el grabador)
- Renderizar `<app-upload-progress [progress]="facade.uploadProgress()" [status]="facade.mediaStatus()">`
- Cuando `mediaStatus === 'ready'`: mostrar `<video>` con `optimized_url` de la respuesta del poller

### 12.3 `src/app/features/tickets/components/ticket-attachments-section/*` + `ticket-execution-page/*`

Mismo patrón que 12.2. El progreso se conecta directamente desde el Observable de `TicketManagementService`.

### 12.4 `src/app/features/satisfaction/components/satisfaction-page/*`

Mismo patrón. El flujo de satisfacción ya recolecta media localmente antes de enviar; adaptar para el nuevo grabador y agregar `media_id` al submit response.

---

## Deployment

- **Servidor/Docker**: instalar el binario de `ffmpeg` y `ffprobe`.
  ```dockerfile
  RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg
  ```
- En `DEPLOY.md`: documentar el requisito del binario y las nuevas variables de entorno.
- **No se agrega ninguna dependencia Python nueva** — sólo `subprocess.run` sobre el binario del sistema.

---

## Archivos relevantes

### Backend — nuevos
| Archivo | Descripción |
|---|---|
| `src/crm_backend/infrastructure/video_processor.py` | VideoProcessor: ffprobe + ffmpeg vía subprocess |
| `src/crm_backend/infrastructure/video_job_repository.py` | CRUD de `video_processing_jobs` |
| `src/crm_backend/services/video_processing_service.py` | VideoProcessingPort + BackgroundTaskVideoProcessingService |
| `src/crm_backend/api/endpoints/media.py` | GET /api/media/{media_id}/status |
| `migrations/versions/xxxx_add_video_processing_jobs.py` | Alembic: tabla video_processing_jobs |
| `migrations/versions/xxxx_add_video_job_id_to_attachments.py` | Alembic: FK en task/ticket attachments |

### Backend — modificados
| Archivo | Cambio |
|---|---|
| `src/crm_backend/core/config.py` | 7 nuevas variables de entorno |
| `src/crm_backend/infrastructure/task_media_storage.py` | Validación MIME/tamaño con nuevos settings; escribe en `raw/` |
| `src/crm_backend/api/endpoints/tasks.py` | Crea job + encola background task |
| `src/crm_backend/api/endpoints/tickets.py` | Ídem |
| `src/crm_backend/api/endpoints/public_tickets.py` | Ídem para satisfacción |
| `src/crm_backend/services/satisfaction_form_service.py` | Ídem |
| `src/crm_backend/api/router.py` | Registra router de media |

### Frontend — nuevos
| Archivo | Descripción |
|---|---|
| `src/app/core/services/video-recorder.service.ts` | MediaRecorder + getUserMedia + codec fallback |
| `src/app/core/services/media-status-poller.service.ts` | Polling GET /api/media/{id}/status |
| `src/app/shared/ui/video-recorder/video-recorder.component.*` | UI de grabación in-app |
| `src/app/shared/ui/upload-progress/upload-progress.component.*` | Barra de progreso + estado de procesamiento |

### Frontend — modificados
| Archivo | Cambio |
|---|---|
| `src/app/core/config/crm-api.config.ts` | `videoMaxDurationSeconds`, `videoMaxUploadMb` |
| `src/app/shared/facades/media-upload.facade.ts` | Señales de progreso + polling post-upload |
| `src/app/shared/facades/media-upload/video-upload.strategy.ts` | Nombre fallback para Blobs sin nombre |
| `src/app/core/services/task-management.service.ts` | `reportProgress: true` |
| `src/app/core/services/ticket-management.service.ts` | `reportProgress: true` |
| `src/app/features/tasks/components/task-attachments-section/*` | Botón grabar + galería + progress component |
| `src/app/features/tickets/components/ticket-attachments-section/*` | Ídem |
| `src/app/features/tickets/components/ticket-execution-page/*` | Progress wiring |
| `src/app/features/satisfaction/components/satisfaction-page/*` | Grabador + progress |

---

## Verificación

1. `npm run build` — sin errores TypeScript
2. Grabar 20 s en Chrome desktop → sube → `status=uploaded` → background task → `status=ready` → `optimized_url` renderiza en UI
3. Grabar > 30 s → auto-stop en frontend a los 30 s → si raw llega con más duración, ffprobe lo rechaza → `status=failed`, error visible
4. Barra de progreso: 0→100 % en el tab Network mientras se transfieren bytes
5. Al 100 %: "Procesando video..." aparece mientras FFmpeg trabaja
6. Al cancelar: la luz de cámara se apaga inmediatamente (todos los tracks detenidos)
7. Permiso denegado: error inline, sin crash, sin pantalla en blanco
8. Android gama baja (Chrome): fallback de codec funciona, al menos `video/webm` disponible
9. Selector de galería: adjuntar `.mp4` existente sigue funcionando + pasa por FFmpeg
10. Formulario de satisfacción: grabador funciona sin autenticación
11. `pytest tests/` — tests existentes pasan; agregar unit tests para `VideoProcessor` y `BackgroundTaskVideoProcessingService`
