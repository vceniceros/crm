# 0024 — In-App Camera Photo Capture

## Problema actual

En algunos Android, después de aceptar una foto con el flujo nativo (`<input capture="environment">`), la app retorna a `/home` o pierde el contexto de la tarea/ticket activa.

## Objetivo

Reemplazar el flujo primario de captura de foto con una captura in-app usando `getUserMedia` + preview de video + `canvas.toBlob`, de forma que el usuario nunca abandone la app y la foto no se guarde en la galería del teléfono.

---

## Regla fundamental

- **MediaRecorder** se usa **solo para video**. No se usa para imágenes.
- Para imágenes: `getUserMedia` → frame de video → `canvas.toBlob`.

---

## Archivos nuevos

| Archivo | Descripción |
|---|---|
| `src/app/core/services/in-app-photo-capture.service.ts` | Servicio que gestiona el stream de cámara y la captura de frame |
| `src/app/shared/ui/photo-capture/photo-capture.component.ts` | Componente de preview y captura |
| `src/app/shared/ui/photo-capture/photo-capture.component.html` | Template del componente |
| `src/app/shared/ui/photo-capture/photo-capture.component.scss` | Estilos del componente |

## Archivos modificados

| Archivo | Cambio |
|---|---|
| `src/app/core/config/crm-api.config.ts` | Agregar `imageMaxUploadMb` al tipo de config y a `crmMediaConfig.image`; actualizar defaults de height y quality |
| `src/app/features/tasks/components/task-attachments-section/task-attachments-section.component.ts` | Integrar `PhotoCaptureComponent` |
| `src/app/features/tasks/components/task-attachments-section/task-attachments-section.component.html` | Reemplazar input con `capture`, integrar `<app-photo-capture>`, relabelar galería |
| `src/app/features/tickets/components/ticket-attachments-section/ticket-attachments-section.component.ts` | Integrar `PhotoCaptureComponent` |
| `src/app/features/tickets/components/ticket-attachments-section/ticket-attachments-section.component.html` | Reemplazar input con `capture`, integrar `<app-photo-capture>`, relabelar galería |

**No se modifican:** formulario de satisfacción (cubierto implícitamente por el cambio en `TicketAttachmentsSectionComponent`), pre-form público (sin adjuntos), backend, modelo de media.

---

## Requisitos

### 1. `InAppPhotoCaptureService`

- Scoped a componente (en `providers: [InAppPhotoCaptureService]` del `PhotoCaptureComponent`, no `providedIn: 'root'`).
- Signals: `isCameraActive = signal(false)`, `errorMessage = signal<string | null>(null)`.
- `startPreview(videoEl: HTMLVideoElement): Promise<void>`
  - Llama `navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false })`.
  - Asigna el stream a `videoEl.srcObject`.
  - Setea `isCameraActive(true)`.
- `capturePhoto(): Promise<File>`
  - Crea un `<canvas>`.
  - Escala el frame manteniendo aspect ratio hasta `crmMediaConfig.image.maxWidth × maxHeight`.
  - Llama `canvas.toBlob('image/jpeg', crmMediaConfig.image.quality)`.
  - Retorna `new File([blob], \`photo-${Date.now()}.jpg\`, { type: 'image/jpeg' })`.
  - Llama `stopTracks()` inmediatamente después de capturar.
- `stopTracks()`: detiene todos los tracks del stream, nula el stream, setea `isCameraActive(false)`.
- `ngOnDestroy()` llama `stopTracks()`.
- Mensajes de error en español: permiso denegado, cámara no disponible, fallo de captura.

### 2. `PhotoCaptureComponent`

- Mirrors the `VideoRecorderComponent` pattern.
- `viewChild<ElementRef<HTMLVideoElement>>('preview')` para el preview en vivo.
- Outputs: `photoCaptured: output<File>()`, `cancelled: output<void>()`.
- `ngOnInit`: inicia el preview.
- `ngOnDestroy`: detiene los tracks.
- Template:
  - `<video #preview autoplay muted playsinline>`
  - Botón "Capturar foto" (deshabilitado hasta que `isCameraActive` sea true)
  - Botón "Cancelar"
  - `<p>` de error inline (visible solo cuando hay error)
- No navega, no guarda en galería, no usa `MediaRecorder`.

### 3. Galería (fallback)

- Mantener `<input type="file" accept="image/*">` existente.
- **Quitar** el atributo `capture="environment"`.
- Label: "Elegir de galería".
- El flujo de subida no cambia.

### 4. Config runtime / env

Agregar a `CrmRuntimeConfig` y `crmMediaConfig.image`:

```
IMAGE_CAPTURE_MAX_WIDTH=1280   → imageMaxWidth (clave existente, default: 1280)
IMAGE_CAPTURE_MAX_HEIGHT=720   → imageMaxHeight (clave existente, default actualizado a 720)
IMAGE_CAPTURE_QUALITY=0.82     → imageQuality (clave existente, default actualizado a 0.82)
IMAGE_MAX_UPLOAD_MB=10         → imageMaxUploadMb (clave nueva, default: 10)
```

> Los primeros tres reutilizan claves ya existentes en `CrmRuntimeConfig`; solo se actualizan los defaults. `imageMaxUploadMb` es la única adición nueva.

### 5. Integración en `task-attachments-section`

```ts
// Agregar en el componente:
readonly isPhotoCaptureOpen = signal(false);

openPhotoCapture(): void { this.isPhotoCaptureOpen.set(true); }
closePhotoCapture(): void { this.isPhotoCaptureOpen.set(false); }
onPhotoCaptured(file: File): void {
  this.isPhotoCaptureOpen.set(false);
  this.uploadFiles([file]);
}
```

```html
<!-- Antes -->
<input #cameraInput type="file" accept="image/*" capture="environment" hidden ... />
<button (click)="openCameraInput(cameraInput)">Cámara foto</button>

<!-- Después -->
<button (click)="openPhotoCapture()">Tomar foto</button>

@if (isPhotoCaptureOpen()) {
  <app-photo-capture
    (photoCaptured)="onPhotoCaptured($event)"
    (cancelled)="closePhotoCapture()"
  />
}

<!-- Galería: quitar capture="environment", relabelar -->
<button (click)="openGalleryInput(galleryInput)">Elegir de galería</button>
```

### 6. Integración en `ticket-attachments-section`

Misma estructura que en `task-attachments-section`. El formulario de satisfacción usa este componente, por lo que queda cubierto automáticamente.

### 7. Sin cambios en backend

- No se modifica el modelo de media, endpoints ni validaciones del backend.
- La lógica de compresión existente (`optimizeImageForUpload`) sigue activa, pero el frame capturado ya viene controlado en dimensiones antes de pasar por ella.

---

## Criterios de verificación

1. `npm run build` sin errores.
2. En Android Chrome: tocar "Tomar foto" abre preview in-app (no la app de cámara nativa, no navega a `/home`).
3. Al capturar: la luz de cámara se apaga inmediatamente.
4. Al cancelar: la luz de cámara se apaga inmediatamente.
5. El archivo capturado sube a través del flujo de media existente sin cambios.
6. "Elegir de galería" abre el selector de archivos normalmente (sin `capture`).
7. La grabación de video (`app-video-recorder`) queda intacta.
8. El formulario de satisfacción sigue funcionando para adjuntar archivos.

---

## Decisiones de diseño

- **Servicio scoped a componente**: evita estado de stream compartido si hay dos secciones de adjuntos en pantalla simultáneamente.
- **Canvas resize con aspect ratio**: el frame capturado ya está limitado en dimensiones antes de que `optimizeImageForUpload` lo procese nuevamente. Doble seguridad, sin bloqueo.
- **Reutilización de claves de config**: `IMAGE_CAPTURE_MAX_WIDTH/HEIGHT/QUALITY` se mapean a las claves existentes `imageMaxWidth`, `imageMaxHeight`, `imageQuality` para no duplicar configuración.
- **`IMAGE_MAX_UPLOAD_MB`**: nueva clave `imageMaxUploadMb` disponible en `crmMediaConfig.image.maxUploadMb` para validación futura en estrategia de subida.
- **Pattern mirror**: `InAppPhotoCaptureService` ↔ `VideoRecorderService`; `PhotoCaptureComponent` ↔ `VideoRecorderComponent`. Consistencia total con el código existente.
