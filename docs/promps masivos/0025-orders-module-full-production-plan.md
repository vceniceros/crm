# 0025 — Orders Module: Full Production-Ready Plan

> **Fecha:** 2026-05-22  
> **Tipo:** Auditoría + Planning  
> **Estado:** Pendiente de implementación  
> **Prerequisito:** Leer antes de implementar cualquier cambio al módulo de pedidos.

---

## A. Executive Summary

No existe un dominio "Orders" separado. "Pedidos" en la UI = `Task` en el modelo de datos. El módulo Tasks **es** el módulo de Orders.

La infraestructura de pre-formularios (tablas, servicio de tokens, endpoint público de submit) es sólida estructuralmente, pero el soporte de campos tipo FILE está completamente roto de punta a punta:

- El modelo de DB tiene columnas `file_attachment_id` que nunca se escriben.
- El endpoint público sólo acepta `text_value`.
- El frontend renderiza campos FILE como `<input type="text">`.

El "formulario de cierre" (post-instalación) **no existe en ninguna capa** del sistema.

---

## B. Estado Actual Confirmado

### Backend

| Componente | Archivo | Estado |
|---|---|---|
| Modelo Task/Order | `models/task_execution.py` | ✅ Completo |
| Enum `TaskStatus` | `models/task_execution.py` | ✅ PENDING, IN_PROGRESS, BLOCKED, PENDING_APPROVAL, COMPLETED |
| Enum `SubtaskType` | `models/task_template.py` | ✅ STANDARD, PRE_FORM — ❌ Sin CLOSE_FORM |
| Modelos pre-form (Instance, Response, FieldValue, Attachment) | `models/task_execution.py` | ✅ Todos definidos — ❌ `Attachment` nunca escrito por ningún endpoint |
| `TaskPreFormFieldValue.file_attachment_id` | `models/task_execution.py` | ✅ Columna FK existe — ❌ NUNCA seteada por `submit_response` |
| GET público pre-form | `api/endpoints/public_tasks.py` | ✅ Funciona |
| POST público pre-form (texto) | `api/endpoints/public_tasks.py` | ✅ Funciona sólo para texto |
| POST público pre-form (archivo) | `api/endpoints/public_tasks.py` | ❌ FALTA — no existe endpoint de upload |
| `submit_response()` | `services/task_pre_form_service.py` | ⚠️ Sólo lee `text_value`, ignora `file_attachment_id` |
| `TaskPreFormFieldValueWriteRequest` | `schemas/tasks.py` | ❌ Sólo tiene `text_value`, sin `file_attachment_id` |
| `TaskMediaStorageFacade` | `infrastructure/task_media_storage.py` | ✅ Estrategias para imágenes/videos — reutilizable |
| Validación magic bytes | `infrastructure/task_media_storage.py` | ❌ FALTA — sólo se confía en el header MIME |
| Rate limiting | `main.py` / middleware | ❌ NINGUNO — endpoints públicos desprotegidos |
| Storage path separado para pre-form | `core/config.py` | ❌ Sin config propia — colisiona con media de tasks |
| Concepto de "formulario de cierre" | todo el backend | ❌ NO EXISTE |
| Expiración de pre-form configurable | `task_pre_form_service.py` | ⚠️ Hardcodeada en 72h (satisfaction form sí tiene config) |
| Captura de User-Agent en pre-form | `task_pre_form_service.py` | ❌ No capturado (satisfaction form sí lo captura) |

### Frontend

| Componente | Archivo | Estado |
|---|---|---|
| Página pública pre-form | `features/pre-form/components/public-task-pre-form-page/` | ✅ Existe |
| Render de campo FILE | `public-task-pre-form-page.component.html` | ❌ Renderiza como `<input type="text">` ("URL o detalle") |
| Facade de upload | `shared/facades/media-upload.facade.ts` | ✅ Existe — ❌ sólo `kind='task'` |
| `file_attachment_id` en payload de submit | `task-management.service.ts` | ❌ NO SE ENVÍA |
| Página de formulario de cierre | todo el frontend | ❌ NO EXISTE |
| Página de ejecución de tarea | `features/tasks/components/task-execution-page/` | ✅ Flujo completo de subtareas |
| Upload de adjuntos de tarea | `task-attachments-section.component.ts` | ✅ Funciona para fotos/videos de tareas |

---

## C. Flujo de Pedido Esperado (end-to-end)

```
1. Admin crea TaskTemplate con subtareas PRE_FORM y/o CLOSE_FORM opcionales
2. Admin/ejecutivo crea Task desde template para un cliente
3. [Opcional] Subtarea PRE_FORM:
   a. Sistema genera token (72h) → link enviado al cliente
   b. Cliente abre URL pública, completa formulario de inicio (texto, opciones, ARCHIVOS)
   c. Al enviar → primera subtarea LOCKED se desbloquea
4. Técnico reclama asignación → inicia trabajo (IN_PROGRESS)
5. Durante el trabajo: técnico sube fotos de evidencia (sistema existente de adjuntos)
6. Técnico completa el trabajo
7. [Opcional] Subtarea CLOSE_FORM:
   a. Interno: técnico completa formulario de cierre en la app
   b. Público: token enviado al cliente para conformidad
   c. Requiere: fotos de evidencia, checklist, notas opcionales
   d. Al enviar → tarea pasa a PENDING_APPROVAL o COMPLETED
8. Ejecutivo revisa si es necesario → COMPLETED
9. Auditoría: todas las respuestas, adjuntos y transiciones se preservan
```

---

## D. Brechas Detectadas

### BLOQUEANTES (no se puede poner Orders en producción sin esto)

| # | Brecha | Capa |
|---|---|---|
| B1 | No existe `POST /public/tasks/pre-form/{token}/attachments` | Backend |
| B2 | `submit_response()` ignora `file_attachment_id` | Backend |
| B3 | `TaskPreFormFieldValueWriteRequest` no tiene campo `file_attachment_id` | Backend |
| B4 | Campos FILE en `public-task-pre-form-page` renderizan como `<input type="text">` | Frontend |
| B5 | Sin upload de archivos en el flujo de submit de pre-form | Frontend |
| B6 | `MediaUploadFacade` sólo soporta `kind='task'` | Frontend |
| B7 | No existe `CLOSE_FORM` en `SubtaskType` — formulario de cierre no existe | Backend+Frontend |
| B8 | Propiedad del attachment no validada en submit (riesgo de contaminación cruzada) | Backend |

### NO BLOQUEANTES (importantes pero no rompen el flujo principal)

| # | Brecha |
|---|---|
| N1 | Sin rate limiting en ningún endpoint público |
| N2 | Header MIME confiado sin validación de magic bytes |
| N3 | Expiración de token de pre-form hardcodeada (no configurable por `.env`) |
| N4 | Sin límite de cantidad de archivos por formulario |
| N5 | Sin storage path separado para uploads públicos de pre-form |
| N6 | User-Agent no capturado en respuestas de pre-form |

### Deuda Técnica

| # | Brecha |
|---|---|
| T1 | Tabla `task_pre_form_attachments` nunca es escrita (infraestructura muerta) |
| T2 | FK `file_attachment_id` en `TaskPreFormFieldValue` nunca se setea |
| T3 | `TaskPreFormStatusResponse` no devuelve URLs de archivos por campo |
| T4 | Sin limpieza de archivos de pre-form huérfanos |

---

## E. Riesgos Técnicos y de Seguridad

| Riesgo | Severidad | Mitigación |
|---|---|---|
| Endpoint público abusado para agotar disco | ALTA | Límite de archivos por token + límite de tamaño + job de limpieza |
| Tipos MIME falsificados aceptados | ALTA | Allowlist + validación de magic bytes (librería `filetype`) |
| Attachment reutilizado en diferente token | ALTA | Validar `attachment.instance_id == instance` en `submit_response` |
| Sin rate limiting en POST públicos | ALTA | `slowapi` o rate limiting a nivel Nginx |
| Paths internos de storage expuestos | MEDIA | Retornar sólo URL pública `/media/...`, nunca el path de storage |
| Archivos huérfanos por fallo parcial de upload | MEDIA | Background task de limpieza si falla el insert en DB |

---

## F. Propuesta de Arquitectura

**Principio central: extender patrones existentes, no reescribir.**

1. **Upload de archivos en pre-form** → nuevo `PreFormMediaStorageFacade` (o re-parametrizar el facade existente con directorio y allowlist diferentes). Sólo imágenes, sin video.

2. **Extensión de `submit_response`** → aceptar `file_attachment_id` por campo; validar que el attachment pertenezca al mismo `instance_id`.

3. **Formulario de cierre** → agregar `CLOSE_FORM` a `SubtaskType`. Agregar columna discriminador `form_phase: Literal['pre','close']` a `TaskTemplatePreForm`. Reutilizar toda la maquinaria de token/instancia/respuesta/attachment. Nuevo `TaskCloseFormService` (wrapper delgado) con lógica diferente de avance de tarea (`→ PENDING_APPROVAL`).

4. **Frontend** → extender `MediaUploadFacade` con `kind: 'pre-form' | 'close-form'`. Reemplazar input de texto. Reutilizar componente de pre-form para close form con input `phase`.

### Capas
```
Router (delgado) → Service (lógica de negocio) → Repository (DB) → Model
                        ↓
               PreFormMediaStorageFacade (I/O de archivos)
```

---

## G. Cambios en Backend

### G1. `core/config.py`
```python
pre_form_expiry_hours: int = 72
pre_form_images_max_bytes: int = 8 * 1024 * 1024      # 8 MB
pre_form_max_attachments_per_instance: int = 10
pre_form_images_dir: Path = crm_media_root_path / "pre_form" / "images"
pre_form_images_public_prefix: str = "/media/pre_form/images"
```

### G2. `schemas/tasks.py`

**Modificar `TaskPreFormFieldValueWriteRequest`:**
```python
class TaskPreFormFieldValueWriteRequest(BaseModel):
    field_id: str
    text_value: str | None = None
    file_attachment_id: str | None = None   # AGREGAR
```

**Modificar `TaskPreFormFieldValueResponse`:**
```python
# Agregar campo:
file_url: str | None = None
```

**Nuevo schema `TaskPreFormAttachmentResponse`:**
```python
class TaskPreFormAttachmentResponse(BaseModel):
    attachment_id: str
    file_url: str
    mime_type: str | None
    uploaded_at: datetime
```

**Modificar `TaskPreFormStatusResponse`:**
```python
# Agregar campo:
attachments: list[TaskPreFormAttachmentResponse] = []
```

### G3. Nuevo `infrastructure/pre_form_media_storage.py`

- `PreFormMediaStorageFacade` — sólo imágenes (JPEG, PNG, WEBP)
- Validación de magic bytes con librería `filetype`
- Bloquear HTML, SVG, ejecutables, scripts
- Límite de tamaño desde config `pre_form_images_max_bytes`
- Directorio desde config `pre_form_images_dir`

### G4. `services/task_pre_form_service.py`

**Nuevo método `upload_attachment` — CONFIRMADO: attachment vinculado a `field_id` específico:**
```python
def upload_attachment(
    self,
    raw_token: str,
    field_id: str,          # REQUERIDO — attachment vinculado a campo específico
    upload_file: UploadFile,
) -> TaskPreFormAttachment:
    instance = self._resolve_token(raw_token)
    # Validar que no esté ya submitted
    if instance.submitted_at is not None:
        raise TaskConflictError("El formulario ya fue enviado.")
    # Validar que field_id existe en la definición del formulario activo
    if instance.template_pre_form is None:
        raise TaskValidationError("El formulario previo no tiene definición válida.")
    field_by_id = {f.field_id: f for f in instance.template_pre_form.fields}
    field = field_by_id.get(field_id)
    if field is None:
        raise TaskValidationError("El campo indicado no pertenece a este formulario.")
    if field.field_type != "FILE":
        raise TaskValidationError("El campo indicado no acepta archivos.")
    # Validar límite de adjuntos por campo
    existing_for_field = [
        a for a in instance.attachments if a.field_id == field_id
    ]
    if len(existing_for_field) >= self._settings.pre_form_max_attachments_per_field:
        raise TaskValidationError("Se alcanzó el límite de archivos para este campo.")
    # Validar límite global por instancia
    if len(instance.attachments) >= self._settings.pre_form_max_attachments_per_instance:
        raise TaskValidationError("Se alcanzó el límite de archivos para este formulario.")
    # Almacenar archivo
    stored = await self._pre_form_storage.store(upload_file)
    attachment = TaskPreFormAttachment(
        instance_id=instance.instance_id,
        field_id=field_id,          # CAMPO NUEVO en el modelo
        file_name=stored.file_name,
        file_url=stored.file_url,
        mime_type=stored.mime_type,
    )
    self._session.add(attachment)
    self._session.commit()
    self._session.refresh(attachment)
    return attachment
```

> **Nota de modelo:** Agregar columna `field_id UUID FK → task_template_pre_form_fields` a `task_pre_form_attachments`. Ver sección I — requiere una migración adicional.

**Cambios en `submit_response` — CONFIRMADO: validar attachment por instancia Y por campo:**
```python
# Agregar parámetro:
submitter_user_agent: str | None = None

# Por cada campo de tipo FILE:
file_attachment_id = (item.get("file_attachment_id") or "").strip() or None
if field.field_type == "FILE":
    if field.is_required and not file_attachment_id:
        raise TaskValidationError(f"El campo obligatorio '{field.label}' requiere un archivo.")
    if file_attachment_id:
        attachment = self._get_attachment(file_attachment_id)
        if attachment is None:
            raise TaskValidationError("El archivo enviado no existe.")
        # Validar que pertenezca a la misma instancia
        if attachment.instance_id != instance.instance_id:
            raise TaskValidationError("El archivo enviado no pertenece a este formulario.")
        # Validar que pertenezca al mismo campo que se está respondiendo
        if attachment.field_id != field.field_id:
            raise TaskValidationError(
                f"El archivo enviado corresponde a otro campo del formulario."
            )
        # Validar que el mismo attachment no satisfaga múltiples campos
        already_used = any(
            fv.file_attachment_id == file_attachment_id
            for fv in response.field_values
        )
        if already_used:
            raise TaskValidationError(
                "El mismo archivo no puede usarse para más de un campo."
            )

response.field_values.append(
    TaskPreFormFieldValue(
        value_id=str(uuid4()),
        field_id=field.field_id,
        text_value=text_value,
        file_attachment_id=file_attachment_id,
    )
)

# Agregar en creación del response:
submitter_user_agent=submitter_user_agent,
```

### G5. `api/endpoints/public_tasks.py`

**Nuevo endpoint — CONFIRMADO: path incluye `field_id`:**
```python
@router.post(
    "/public/tasks/pre-form/{token}/fields/{field_id}/attachments",
    response_model=TaskPreFormAttachmentResponse,
    responses={
        404: {"description": "Token expirado, usado o no encontrado"},
        409: {"description": "Formulario ya enviado"},
        413: {"description": "Archivo demasiado grande"},
        415: {"description": "Tipo de archivo no permitido"},
        422: {"description": "Campo inválido / no es tipo FILE / límite alcanzado"},
        429: {"description": "Demasiadas solicitudes"},
    },
)
async def upload_public_pre_form_attachment(
    token: str,
    field_id: str,
    file: UploadFile = File(...),
    pre_form_service: TaskPreFormService = Depends(get_task_pre_form_service),
) -> TaskPreFormAttachmentResponse:
    attachment = await pre_form_service.upload_attachment(
        raw_token=token,
        field_id=field_id,
        upload_file=file,
    )
    return TaskPreFormAttachmentResponse(
        attachment_id=attachment.attachment_id,
        file_url=attachment.file_url,
        mime_type=attachment.mime_type,
        uploaded_at=attachment.uploaded_at,
    )
```

**Modificar `submit_public_task_pre_form`** para pasar `User-Agent` al servicio.

### G6. Formulario de Cierre (nueva funcionalidad)

**`models/task_template.py`:**
```python
class SubtaskType(StrEnum):
    STANDARD = "standard"
    PRE_FORM = "pre_form"
    CLOSE_FORM = "close_form"   # AGREGAR
```

**`models/task_execution.py` — `TaskTemplatePreForm`:**
```python
form_phase: Mapped[str] = mapped_column(
    String(10), default="pre", server_default="pre"
)
# CHECK (form_phase IN ('pre', 'close')) — en migración
```

**Nuevo método de avance — CONFIRMADO: siempre → `PENDING_APPROVAL`:**
```python
def _advance_task_after_close_form(self, instance: TaskPreFormInstance, now: datetime) -> None:
    task = instance.task
    # DECISIÓN CONFIRMADA: el close form nunca auto-completa la tarea.
    # La finalización requiere aprobación explícita de ejecutivo/admin.
    task.status = TaskStatus.PENDING_APPROVAL
```

> **Justificación:** El close form certifica que el lado de campo terminó, pero siempre queda pendiente una validación/configuración remota final. La aprobación explícita reutiliza el flujo `PENDING_APPROVAL → COMPLETED` ya implementado.

**Nuevos endpoints:**
```
GET  /public/tasks/close-form/{token}
POST /public/tasks/close-form/{token}
POST /public/tasks/close-form/{token}/attachments
```

### G7. Seguridad (middleware)

- Agregar `slowapi` rate limiting: 10 req/min por IP en todas las rutas `/public/`
- Agregar límite por token: 30 uploads por token por hora

### G8. Migraciones Alembic (3 requeridas)

```sql
-- Migración 1: User-Agent en respuestas de pre-form
ALTER TABLE task_pre_form_responses
  ADD COLUMN submitter_user_agent VARCHAR(500) NULL;

-- Migración 2: Discriminador de fase en definición de formulario
ALTER TABLE task_template_pre_forms
  ADD COLUMN form_phase VARCHAR(10) NOT NULL DEFAULT 'pre'
  CHECK (form_phase IN ('pre', 'close'));

-- Migración 3: Extender constraint de tipo de subtarea
ALTER TABLE task_template_subtasks
  DROP CONSTRAINT IF EXISTS subtask_type_check;
ALTER TABLE task_template_subtasks
  ADD CONSTRAINT subtask_type_check
  CHECK (subtask_type IN ('standard', 'pre_form', 'close_form'));
```

> **Nota:** La tabla `task_pre_form_attachments` ya existe. No se requieren nuevas tablas.

---

## H. Cambios en Frontend

### H1. `public-task-pre-form-page.component.html+ts`

**Cambio crítico — campo FILE:**
```html
<!-- ANTES (incorrecto): -->
<input matInput placeholder="Referencia del archivo (URL o detalle)" />

<!-- DESPUÉS (correcto): -->
<input
  type="file"
  accept="image/jpeg,image/png,image/webp"
  capture="environment"
  (change)="onFileSelected($event, field)"
/>
```

**Estrategia: upload-on-select** (recomendada — ver sección O.4).

**Estado por campo FILE:**
```typescript
type FileUploadState = 'idle' | 'uploading' | 'uploaded' | 'error';

interface FieldUploadState {
  state: FileUploadState;
  attachmentId: string | null;
  fileName: string | null;
  errorMessage: string | null;
}
```

**Reglas de UX:**
- Validar tamaño/tipo antes de llamar al backend
- Mostrar progreso durante upload
- Botón "Reintentar" en caso de error
- Bloquear "Enviar" mientras hay un upload en curso
- Preservar todos los demás campos al fallar un upload

**Payload de submit extendido:**
```typescript
// En submitPublicTaskPreForm():
const values = fields.map(field => {
  if (field.field_type === 'FILE') {
    return {
      field_id: field.field_id,
      text_value: null,
      file_attachment_id: this.fileStates[field.field_id]?.attachmentId ?? null,
    };
  }
  return { field_id: field.field_id, text_value: this.formValues[field.field_id] };
});
```

### H2. `shared/facades/media-upload.facade.ts`

```typescript
// Extender UploadKind — CONFIRMADO: pre-form y close-form incluyen field_id en path:
type UploadKind = 'task' | 'pre-form' | 'close-form';

// Mapeo de kind a endpoint:
private getUploadUrl(kind: UploadKind, contextId: string, fieldId?: string): string {
  switch (kind) {
    case 'task':
      return `${this.baseUrl}/tasks/${contextId}/attachments`;
    case 'pre-form':
      if (!fieldId) throw new Error('fieldId requerido para pre-form upload');
      return `${this.baseUrl}/public/tasks/pre-form/${contextId}/fields/${fieldId}/attachments`;
    case 'close-form':
      if (!fieldId) throw new Error('fieldId requerido para close-form upload');
      return `${this.baseUrl}/public/tasks/close-form/${contextId}/fields/${fieldId}/attachments`;
  }
}
```

### H3. Nueva `features/pre-form/components/public-task-close-form-page/`

- Reutilizar estructura de `public-task-pre-form-page` con `@Input() phase: 'close'`
- Misma lógica de render de campos
- Campos de evidencia requerida marcados visualmente
- Checkbox de conformidad si aplica

### H4. `features/tasks/components/task-execution-page/`

- Detectar subtarea con tipo `CLOSE_FORM`
- Mostrar acción "Completar formulario de cierre"
- Formulario interno: técnico sube fotos + completa checklist

### H5. `core/services/task-management.service.ts`

```typescript
// Agregar:
uploadPreFormAttachment(token: string, file: File): Observable<PreFormAttachment> { ... }
getPublicTaskCloseForm(token: string): Observable<PublicTaskCloseFormInfoResponse> { ... }
submitPublicTaskCloseForm(token: string, values: TaskPreFormFieldValueWrite[]): Observable<{ status: string }> { ... }
```

### H6. `app/app.routes.ts`

```typescript
// Agregar ruta pública:
{
  path: 'close-form/:token',
  loadComponent: () => import('./features/pre-form/components/public-task-close-form-page/...'),
  // Sin guard de autenticación
},
```

---

## I. Cambios en Base de Datos

Cuatro migraciones Alembic. **No se requieren tablas nuevas.**

```sql
-- Migración 1
ALTER TABLE task_pre_form_responses
  ADD COLUMN submitter_user_agent VARCHAR(500) NULL;

-- Migración 2
ALTER TABLE task_template_pre_forms
  ADD COLUMN form_phase VARCHAR(10) NOT NULL DEFAULT 'pre'
  CHECK (form_phase IN ('pre', 'close'));

-- Migración 3
ALTER TABLE task_template_subtasks
  DROP CONSTRAINT IF EXISTS subtask_type_check;
ALTER TABLE task_template_subtasks
  ADD CONSTRAINT subtask_type_check
  CHECK (subtask_type IN ('standard', 'pre_form', 'close_form'));

-- Migración 4 — REQUERIDA por decisión confirmada: attachment vinculado a field_id
ALTER TABLE task_pre_form_attachments
  ADD COLUMN field_id UUID NULL
  REFERENCES task_template_pre_form_fields(field_id) ON DELETE SET NULL;
CREATE INDEX idx_pre_form_attachments_field_id ON task_pre_form_attachments(field_id);
```

`task_pre_form_attachments` ya existe y se reutiliza para ambas fases. La nueva columna `field_id` es nullable para compatibilidad con registros anteriores (si los hubiera).

---

## J. Contratos de API

### J1. Upload adjunto de pre-form (PÚBLICO, nuevo) — `field_id` en path

```
POST /public/tasks/pre-form/{token}/fields/{field_id}/attachments
Content-Type: multipart/form-data
Body:
  - file: binary (requerido)

Validaciones ejecutadas por el backend:
  1. token válido y no expirado
  2. formulario no enviado aún (submitted_at IS NULL)
  3. field_id existe en la definición del formulario activo
  4. field.field_type == "FILE"
  5. cantidad de adjuntos para ese field_id < pre_form_max_attachments_per_field
  6. cantidad total de adjuntos para la instancia < pre_form_max_attachments_per_instance
  7. MIME type + magic bytes en allowlist (JPEG, PNG, WEBP)
  8. tamaño ≤ pre_form_images_max_bytes

→ 200: { "attachment_id": "uuid", "file_url": "/media/pre_form/images/abc.jpg",
          "mime_type": "image/jpeg", "uploaded_at": "2026-05-22T10:00:00Z" }
→ 404: token expirado/usado/no encontrado
→ 409: formulario ya enviado
→ 413: archivo demasiado grande
→ 415: tipo no permitido
→ 422: field_id inválido / campo no es tipo FILE / límite alcanzado
→ 429: rate limit
```

### J2. Submit pre-form con archivo (PÚBLICO, extendido)

```
POST /public/tasks/pre-form/{token}
Content-Type: application/json

{
  "values": [
    { "field_id": "uuid-campo-texto", "text_value": "Notas del cliente" },
    { "field_id": "uuid-campo-file",  "text_value": null, "file_attachment_id": "uuid-attachment" }
  ]
}

→ 200: { "response_id": "...", "task_id": "...", "submitted_at": "...", "status": "ok" }
→ 422: campo FILE requerido sin attachment_id
→ 422: attachment pertenece a otro token
```

### J3. Estado de pre-form con URLs de archivos (AUTENTICADO, extendido)

```
GET /tasks/{task_id}/pre-form/status

→ 200: {
    "instance_id": "...",
    "status_label": "...",
    "response_values": [
      { "field_id": "...", "label": "...", "text_value": null,
        "file_url": "/media/pre_form/images/abc.jpg" }
    ]
  }
```

### J4. Formulario de cierre (PÚBLICO, nuevo)

```
GET  /public/tasks/close-form/{token}                                    → PublicTaskCloseFormInfoResponse
POST /public/tasks/close-form/{token}                                    → { response_id, status: "ok" }
POST /public/tasks/close-form/{token}/fields/{field_id}/attachments      → { attachment_id, file_url, ... }
```

> Mismas reglas de validación de `field_id` que en J1. El submit del close form avanza la tarea a `PENDING_APPROVAL` (ver J5).

### J5. Transición de estado al enviar close form — CONFIRMADO

```
POST /public/tasks/close-form/{token}
→ 200: { response_id, status: "ok" }
→ Efecto de estado:
    task.status: IN_PROGRESS → PENDING_APPROVAL
    (nunca → COMPLETED automáticamente)
```

**Flujo de aprobación reutilizado:**
```
task.status == PENDING_APPROVAL
    → ejecutivo/admin ejecuta acción de aprobación existente
    → task.status == COMPLETED
```

> **Nota sobre descarga segura:** Para MVP, los archivos se sirven vía static mount existente (`/media/`). Los archivos de pre-form estarán bajo `/media/pre_form/images/` (path separado). No se requiere signed URL para MVP — acceso por conocer la URL es aceptable para fotos de conformidad no sensibles. Para datos sensibles, evaluar endpoint de descarga con validación de sesión en el futuro.

---

## K. Statuses y Reglas de Negocio

### Statuses existentes — conservar tal cual

```
PENDING → IN_PROGRESS → BLOCKED → PENDING_APPROVAL → COMPLETED
```

### Reglas a implementar

| Regla | Dónde se hace cumplir |
|---|---|
| Campo FILE requerido → submit bloqueado sin `file_attachment_id` | `submit_response()` |
| Attachment debe pertenecer al mismo token/instancia | `submit_response()` — validación nueva |
| Máximo de adjuntos por instancia | `upload_attachment()` — guard nuevo |
| Token expirado → 404 | `_resolve_token()` — ya funciona |
| Doble submit → 409 | `is_usable` — ya funciona |
| Submit close form → tarea SIEMPRE → `PENDING_APPROVAL`, nunca auto-COMPLETED | nuevo `_advance_task_after_close_form()` — CONFIRMADO |
| Quién puede generar link de pre-form | `generate_or_regenerate_link` — ya implementado: admin/ejecutivo |
| Quién puede ver respuestas | `get_task_detail` — ya implementado con auth |
| Quién puede aprobar cierre | `execute_subtask_action` — ya implementado con roles |

### Reglas configurables por tipo de pedido (futuro, no MVP)

- Si se requiere formulario de inicio por tipo de pedido
- Si se requiere formulario de cierre por tipo de pedido
- Evidencia fotográfica mínima requerida
- Quién puede completar cada formulario (por `role_key`)

---

## L. Fases de Implementación

### Fase 1 — Upload de archivos en pre-form (BLOQUEANTES)
*~3-4 días — resolver B1..B6 y B8*

**Backend (pueden ejecutarse en paralelo después del paso 1):**
1. Agregar config de pre-form a `Settings`
2. Crear `PreFormMediaStorageFacade` en `infrastructure/`
3. Agregar `upload_attachment()` a `TaskPreFormService`
4. Agregar `POST /public/tasks/pre-form/{token}/attachments` *(depende de 2, 3)*
5. Agregar `file_attachment_id` a `TaskPreFormFieldValueWriteRequest`
6. Actualizar `submit_response()` *(depende de 5)*
7. Agregar captura de `submitter_user_agent` + migración

**Frontend (paralelo con backend):**
8. Reemplazar campo FILE con `<input type="file">` + soporte cámara
9. Extender `MediaUploadFacade` para `kind: 'pre-form'`
10. Agregar gestión de estado de upload al componente *(depende de 9)*
11. Incluir `file_attachment_id` en payload de submit *(depende de 10)*
12. Validación client-side de tamaño/tipo antes del upload

**Validar:** `npm run build` pasa sin errores; test E2E manual de upload de archivo en pre-form.

---

### Fase 2 — Hardening de Seguridad (NO BLOQUEANTE, alta prioridad)
*~1-2 días — resolver N1..N5*

13. Agregar librería `filetype` + validación de magic bytes en `PreFormMediaStorageFacade`
14. Agregar rate limiting `slowapi` para rutas `/public/` (o confirmar que Nginx lo maneja)
15. Agregar guard de cantidad máxima de adjuntos por token
16. Hacer expiración de pre-form configurable vía `.env`
17. Extender `TaskPreFormStatusResponse` con `file_url` por campo

---

### Fase 3 — Formulario de cierre (nueva funcionalidad)
*~4-5 días — resolver B7*

**Backend:**
18. Agregar `CLOSE_FORM` a `SubtaskType` + migración
19. Agregar `form_phase` a `TaskTemplatePreForm` + migración
20. Extender servicio con ciclo de vida de formulario de cierre + `_advance_task_after_close_form()`
21. Agregar endpoints `GET/POST /public/tasks/close-form/{token}` + `/attachments`

**Frontend:**
22. Crear `PublicTaskCloseFormPage` (reutilizar estructura de pre-form)
23. Agregar ruta `/close-form/:token`
24. Extender `MediaUploadFacade` para `kind: 'close-form'`
25. Agregar punto de entrada de formulario de cierre en `task-execution-page`
26. Extender `task-management.service.ts` con llamadas de API de close form

---

### Fase 4 — Vista de detalle de pedido + audit trail
*~1-2 días*

27. Mostrar respuesta de pre-form con thumbnails de adjuntos en detalle de tarea
28. Mostrar respuesta de close form con thumbnails en detalle de tarea
29. Agregar background task de limpieza de archivos huérfanos
30. Log de auditoría completo para eventos de upload público (IP hash, user-agent, token, timestamp)

---

## M. QA Checklist

### Upload de archivos en pre-form

- [ ] Cliente puede seleccionar imagen vía cámara en mobile (Android + iOS)
- [ ] Imagen mayor al límite rechazada client-side con mensaje claro
- [ ] Formato inválido (PDF, EXE, SVG) rechazado en backend con mensaje claro
- [ ] `attachment_id` almacenado en estado del componente tras upload exitoso
- [ ] Campo FILE requerido bloquea submit sin archivo
- [ ] Campo FILE opcional permite submit sin archivo
- [ ] Attachment de token diferente rechazado en submit
- [ ] Token expirado → 404 al intentar upload
- [ ] Token ya enviado → 409 al intentar upload
- [ ] Límite de cantidad de uploads superado → error claro
- [ ] Estado del formulario preservado tras cancelar file picker o error de upload
- [ ] Reintento tras upload fallido funciona
- [ ] `npm run build` pasa sin errores nuevos

### Formulario de cierre

- [ ] Token de close form generado al dispararse cierre por técnico
- [ ] Cliente completa formulario de cierre con fotos de evidencia requeridas
- [ ] Submit avanza tarea a `PENDING_APPROVAL`
- [ ] Ejecutivo ve respuestas de close form con thumbnails de fotos

### Regresión (no debe romperse)

- [ ] Submit de pre-form sólo texto sigue funcionando
- [ ] Upload de adjuntos de tareas/tickets no afectado
- [ ] Flujo de completion de subtareas no afectado
- [ ] Formulario de satisfacción no afectado
- [ ] Reenvío/regeneración de link de pre-form sigue funcionando

---

## N. Casos de Prueba Mínimos

### Backend (pytest)

```python
# 1. Upload exitoso
test_upload_pre_form_attachment_success
# → token válido, JPEG válido → 200, attachment_id retornado

# 2. Token expirado
test_upload_pre_form_attachment_expired_token
# → 404

# 3. Formulario ya enviado
test_upload_pre_form_attachment_already_submitted
# → 409

# 4. MIME type inválido (spoofed Content-Type)
test_upload_pre_form_attachment_invalid_mime
# → 422

# 5. Archivo demasiado grande
test_upload_pre_form_attachment_oversized
# → 413

# 6. Submit con file_attachment_id válido
test_submit_pre_form_with_valid_file_attachment_id
# → success, field_value.file_attachment_id seteado en DB

# 7. Attachment de otra instancia en submit
test_submit_pre_form_with_wrong_instance_attachment
# → error de validación

# 8. Campo FILE requerido sin archivo
test_submit_pre_form_required_file_field_missing
# → 422

# 9. Límite de adjuntos superado
test_upload_pre_form_max_attachments_exceeded
# → 422

# 10. Formulario de cierre avanza tarea
test_close_form_submit_advances_task_to_pending_approval
# → task.status == PENDING_APPROVAL
```

### Frontend (Cypress/Playwright)

```
11. Campo FILE muestra file picker al hacer click
12. Indicador de progreso visible durante upload
13. Tras upload, campo muestra estado "uploaded" con thumbnail
14. Payload de submit incluye file_attachment_id para campos FILE
15. Mensaje de error mostrado en 413/422 con botón de reintento
```

---

## O. Decisiones que Requieren Validación Humana

### O.1 — ¿Formulario de cierre: público vs interno para el MVP?

| Opción | Descripción |
|---|---|
| **A (recomendada)** | Interno primero (técnico lo completa en la app) → agregar token público como segunda etapa |
| **B** | Token público (conformidad del cliente) desde el inicio de la Fase 3 |

> **Impacto:** Opción B duplica el scope de Fase 3. Confirmar antes de arrancar.

---

### ✅ DC-1 — DECISIÓN CONFIRMADA: CLOSE_FORM siempre → `PENDING_APPROVAL`

**Resolución:** El submit del close form nunca auto-completa la tarea. Siempre transiciona a `PENDING_APPROVAL`.

**Justificación:** El close form certifica que el lado de campo/operador terminó su parte (evidencia fotográfica, configuración final conocida), pero el sistema contempla una etapa de validación/configuración remota posterior. La finalización definitiva requiere una acción explícita de aprobación por parte de un ejecutivo o admin autorizado.

**Transición requerida:**
```
IN_PROGRESS
  → submit CLOSE_FORM
  → PENDING_APPROVAL          ← siempre, sin excepción en MVP
  → validación/configuración remota final
  → acción de aprobación explícita
  → COMPLETED
```

**Regla de negocio:**
- Submittear el close form NO cierra la tarea.
- Solo confirma que el trabajo de campo terminó.
- El cierre definitivo es siempre una acción de aprobación separada.
- Reutilizar los roles y el flujo de aprobación existente (`PENDING_APPROVAL → COMPLETED`) sin crear un nuevo status.

**Impacto en implementación:**
- En `_advance_task_after_close_form()`: `task.status = TaskStatus.PENDING_APPROVAL` — sin condicional.
- No agregar lógica de auto-complete en MVP.

---

### ✅ DC-2 — DECISIÓN CONFIRMADA: attachment vinculado a `field_id` específico

**Resolución:** El endpoint de upload público debe asociar cada archivo a un campo específico del formulario, no sólo a la instancia.

**Endpoint confirmado:**
```
POST /public/tasks/pre-form/{token}/fields/{field_id}/attachments
POST /public/tasks/close-form/{token}/fields/{field_id}/attachments
```

**Validaciones requeridas en el backend:**
1. Token válido y no expirado.
2. Formulario no enviado aún (`submitted_at IS NULL`).
3. `field_id` existe en la definición del formulario activo.
4. `field.field_type == "FILE"`.
5. Cantidad de adjuntos para ese `field_id` no excede `pre_form_max_attachments_per_field`.

**Validaciones en `submit_response`:**
- `file_attachment_id` pertenece a la misma instancia.
- `file_attachment_id` pertenece al mismo `field_id` que se está respondiendo.
- El mismo `attachment_id` no puede satisfacer más de un campo FILE.

**Impacto en modelo de datos:**
- Agregar columna `field_id UUID NULL FK → task_template_pre_form_fields` a `task_pre_form_attachments`.
- Requiere Migración 4 (ver sección I).
- `field_id` nullable para compatibilidad retroactiva.

**Impacto en config:**
- Agregar `pre_form_max_attachments_per_field: int = 3` a `Settings`.

---

### O.2 — ¿Rate limiting: a nivel app o a nivel Nginx?

| Opción | Descripción |
|---|---|
| **A (recomendada)** | `slowapi` en la app como salvaguarda + límite externo en Nginx |
| **B** | Sólo Nginx — sin cambios en código de app |

> Si producción ya tiene rate limiting en Nginx para `/public/`, la Opción B es suficiente para el MVP.

---

### O.3 — ¿Librería para validación de magic bytes?

| Opción | Dependencia | Nota |
|---|---|---|
| **`filetype` (recomendada)** | Pure Python, sin deps del sistema | `pip install filetype` |
| **`python-magic`** | Requiere `libmagic` en el servidor | Más precisa pero compleja en deploy |

> Confirmar con infra si `libmagic` está disponible en la imagen Docker de producción.

---

### O.4 — ¿Upload inmediato (on-select) vs upload al enviar (on-submit)?

| Opción | Pros | Contras |
|---|---|---|
| **On-select (recomendada)** | Sin riesgo de timeout, UX clara, `attachment_id` listo antes del submit | Archivos huérfanos si se abandona el formulario (mitigado con cleanup job) |
| **On-submit** | Sin archivos huérfanos | Riesgo de timeout en conexiones móviles lentas, submit más complejo |

---

### O.5 — ¿Separar dominio Orders vs mantener Tasks como Orders?

| Opción | Impacto |
|---|---|
| **Mantener Tasks = Orders (recomendada)** | Cero refactor, máxima estabilidad |
| Separar en dominio propio | Refactor masivo sin ganancia funcional en el corto plazo |

> Para distinguir tipos de pedido (instalación DVR vs reparación de cable, etc.), usar `category_id` ya existente en el modelo `Task`. No se requiere tabla nueva.

---

*Fin del documento de planning. No implementar hasta confirmar las decisiones en sección O.*
