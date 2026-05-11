# 0013 — Extensión del módulo de Pedidos (ex Tareas)

## Objetivo

Extender el módulo de tareas para igualarlo funcionalmente al de tickets, agregar
semántica de "pedidos" en la capa de presentación, y sumar dos funcionalidades
nuevas: flags operativos (`requiere llegada` / `requiere multimedia para cerrar`),
exportación PDF, encuesta de satisfacción, y un **formulario previo** configurable
por template que el cliente llena antes de que empiece el trabajo.

---

## Decisiones de diseño confirmadas

| Decisión | Elección |
|---|---|
| Pre-form en el flujo de subtareas | Columna `subtask_type` en `subtasks` y `template_subtasks` (`'pre_form'` / `'standard'`) |
| Encuesta de satisfacción para pedidos | Reusar `SatisfactionPageComponent` con query param `?mode=task` |
| URLs | Mantener `/tasks`. Solo cambia el texto visible en UI |

---

## Gaps actuales relevados en el código

- `TaskComment` existe pero **no tiene `location_id`** (el de ticket sí lo tiene).
- `TaskCommentType` solo tiene `GENERAL / TRANSITION / PROGRESS` — le faltan `CLOSURE`, `ARRIVAL_REGISTRATION`, `CLOSURE_EVIDENCE`.
- No existe endpoint `POST /tasks/{task_id}/comments` (comentarios solo se crean internamente desde acciones de subtarea).
- `Task` no tiene `requires_arrival_comment`, `requires_video_evidence`, `arrival_registered_at`, `arrival_comment_id`.
- No hay servicio de exportación PDF para tareas.
- No hay sistema de encuesta de satisfacción para tareas.
- No hay sistema de formulario previo.

---

## Phase 1 — Comentarios ricos en pedidos (multimedia + ubicación)

### Backend

1. **Migración**: agregar columna `location_id` (FK → `locations`) en tabla `task_comments`.
2. Actualizar modelo `TaskComment` ([`models/task_execution.py`](../../microtv-crm-backend/src/crm_backend/models/task_execution.py)): agregar `location_id` + relación `location`.
3. Extender enum `TaskCommentType`: agregar `CLOSURE`, `ARRIVAL_REGISTRATION`, `CLOSURE_EVIDENCE`.
4. Actualizar schema `TaskCommentResponse` ([`schemas/tasks.py`](../../microtv-crm-backend/src/crm_backend/schemas/tasks.py)): agregar `location: LocationResponse | None`.
5. Agregar schema `CreateTaskCommentRequest`: `body`, `location_id`, `attachment_ids`.
6. Agregar método `add_task_comment()` en [`services/tasks/application.py`](../../microtv-crm-backend/src/crm_backend/services/tasks/application.py).
7. Agregar endpoint `POST /tasks/{task_id}/comments` en [`api/endpoints/tasks.py`](../../microtv-crm-backend/src/crm_backend/api/endpoints/tasks.py).

### Frontend

1. Actualizar interfaz `TaskComment` en [`task-management.model.ts`](../../microtv-crm-frontend/src/app/core/models/task-management.model.ts): agregar `location`, `comment_type`.
2. Agregar `addTaskComment()` en [`task-management.service.ts`](../../microtv-crm-frontend/src/app/core/services/task-management.service.ts).
3. Agregar panel compositor de comentarios en [`task-execution-page`](../../microtv-crm-frontend/src/app/features/tasks/components/task-execution-page/task-execution-page.component.ts) (location picker + adjuntos vinculados, modelado sobre el equivalente de ticket).
4. Renderizar timeline de comentarios con slider multimedia y chip de ubicación.
5. Reusar o adaptar el componente `task-attachments-section` ya existente.

---

## Phase 2 — `requiere_llegada` + `requiere_multimedia_para_cerrar`

### Backend

1. **Migración**: agregar en tabla `tasks`:
   - `requires_arrival_comment BOOLEAN DEFAULT false`
   - `requires_video_evidence BOOLEAN DEFAULT false`
   - `arrival_registered_at TIMESTAMPTZ NULL`
   - `arrival_comment_id UUID NULL FK → task_comments`
2. **Migración**: agregar los mismos flags como defaults en tabla `task_templates`.
3. Actualizar modelos `Task` y `TaskTemplate`.
4. Actualizar schemas: `CreateTaskFromTemplateRequest` y `TaskTemplateResponse` deben exponer los flags.
5. Al instanciar una tarea desde template: copiar los flags.
6. Lógica de servicio:
   - Bloquear finalización de tarea si `requires_arrival_comment` y llegada no registrada.
   - Bloquear finalización si `requires_video_evidence` y el comentario de cierre no tiene video.
   - Auto-registrar llegada cuando se agrega un comentario con multimedia + ubicación.

### Frontend

1. Agregar `requires_arrival_comment`, `requires_video_evidence` al modelo `TaskDetail`.
2. Agregar checkboxes en el formulario de creación de tarea en [`tasks-page.component`](../../microtv-crm-frontend/src/app/features/tasks/components/tasks-page/tasks-page.component.ts).
3. Agregar checkboxes a nivel template en [`task-template-form-page`](../../microtv-crm-frontend/src/app/features/task-templates/components/task-template-form-page/task-template-form-page.component.ts).
4. Agregar computed signals de bloqueo + banner de estado de llegada en `task-execution-page` (igual que el ticket).

---

## Phase 3 — Renombrado semántico: tareas → pedidos (solo frontend, solo display)

> **Alcance estricto**: solo texto visible al usuario. Rutas, nombres de archivos, endpoints, campos de modelo y keys en JSON **no cambian**.

Archivos a actualizar:

| Archivo | Qué cambia |
|---|---|
| [`app.routes.ts`](../../microtv-crm-frontend/src/app/app.routes.ts) | `data.title` de todas las rutas de tasks |
| [`src/mocks/layout-data.json`](../../microtv-crm-frontend/src/mocks/layout-data.json) | `label` del menú lateral |
| Todos los `.html` en `features/tasks/` y `features/task-templates/` | Eyebrows, títulos, subtítulos, mensajes, labels de botones |
| `.ts` con strings hardcodeados de display | `pageTitle`, `eyebrow`, mensajes de error, labels |
| `UI_HELP_TEXTS.tasks` si existe | Textos de ayuda contextual |

Vocabulario de reemplazo:

| Original | Nuevo |
|---|---|
| Tarea | Pedido |
| Tareas | Pedidos |
| Template de tarea | Template de pedido |
| Templates de tareas | Templates de pedidos |
| Crear tarea | Crear pedido |
| Ejecución de tarea | Ejecución de pedido |
| Subtarea | Subtarea *(sin cambio)* |

---

## Phase 4 — Exportación PDF + Encuesta de satisfacción para pedidos

### Backend — PDF

1. Crear `task_export_service.py` modelado sobre [`ticket_export_service.py`](../../microtv-crm-backend/src/crm_backend/services/ticket_export_service.py).
   - Secciones: cabecera del pedido, timeline de subtareas, comentarios + fotos embebidas, bloque de encuesta.
2. Agregar endpoint `GET /tasks/{task_id}/export` en [`api/endpoints/tasks.py`](../../microtv-crm-backend/src/crm_backend/api/endpoints/tasks.py).

### Backend — Encuesta de satisfacción

1. Nuevas tablas: `task_satisfaction_forms`, `task_satisfaction_responses` (espejo de las de ticket).
2. Nuevos modelos `TaskSatisfactionForm`, `TaskSatisfactionResponse` en `task_execution.py`.
3. Nuevo servicio `task_satisfaction_form_service.py` (espejo de [`satisfaction_form_service.py`](../../microtv-crm-backend/src/crm_backend/services/satisfaction_form_service.py)).
4. Endpoints internos:
   - `POST /tasks/{task_id}/satisfaction-form`
   - `GET /tasks/{task_id}/satisfaction-form/status`
   - `GET /tasks/{task_id}/satisfaction-response`
5. Endpoint público: `POST /satisfaction/task/{token}` (sin autenticación).
6. Migraciones correspondientes.

### Frontend

1. Agregar botón de exportar PDF en `task-execution-page` (solo pedidos completados).
2. Agregar botones "Generar encuesta" / "Ver encuesta" en `task-execution-page`.
3. Reusar [`survey-link-dialog`](../../microtv-crm-frontend/src/app/features/tickets/components/survey-link-dialog/) sin modificaciones o con mínimos ajustes de label.
4. Reusar [`SatisfactionPageComponent`](../../microtv-crm-frontend/src/app/features/satisfaction/components/satisfaction-page/satisfaction-page.component.ts) mediante query param `?mode=task`:
   - La ruta pública `satisfaction/:token?mode=task` ya existe (no se necesita nueva ruta).
   - El componente lee `mode` desde `ActivatedRoute.queryParams` y llama al endpoint de pedidos.

---

## Phase 5 — Formulario Previo

El formulario previo es la primera subtarea de tipo `'pre_form'`. El cliente lo llena
mediante un link seguro antes de que el equipo técnico arranque. Es opcional y
configurable en el template.

### Backend — Nuevos modelos

| Modelo | Tabla | Descripción |
|---|---|---|
| `TaskTemplatePreForm` | `task_template_pre_forms` | Definición del formulario (1:1 con template) |
| `TaskTemplatePreFormField` | `task_template_pre_form_fields` | Campo individual: label, field_type, is_required, order_index, placeholder |
| `TaskPreFormInstance` | `task_pre_form_instances` | Instancia segura por tarea (token_hash, expires_at, submitted_at, revoked_at) |
| `TaskPreFormResponse` | `task_pre_form_responses` | Respuesta del cliente |
| `TaskPreFormFieldValue` | `task_pre_form_field_values` | Valor por campo (text_value, file_attachment_id) |
| `TaskPreFormAttachment` | `task_pre_form_attachments` | Archivos subidos para campos tipo FILE |

**Tipos de campo soportados** (`field_type` enum):

| Valor | Input HTML equivalente | Descripción |
|---|---|---|
| `TEXT` | `<input type="text">` | Texto corto |
| `NUMBER` | `<input type="number">` | Numérico |
| `TEXTAREA` | `<textarea>` | Texto largo |
| `DATE` | `<input type="date">` | Fecha |
| `TEL` | `<input type="tel">` | Número de teléfono |
| `FILE` | `<input type="file" accept="image/*,video/*">` | Multimedia |
| `CHECKBOX` | `<input type="checkbox">` | Casilla booleana |

### Backend — Cambios en template y tarea

1. **Migración**: agregar `requires_pre_form BOOLEAN DEFAULT false` en `task_templates`.
2. **Migración**: agregar `subtask_type VARCHAR(50) DEFAULT 'standard'` en `template_subtasks` y `subtasks`.
3. Actualizar `TaskTemplate`: agregar `requires_pre_form` + relación `pre_form → TaskTemplatePreForm`.
4. Actualizar schemas `CreateTaskTemplateRequest` / `UpdateTaskTemplateRequest`:
   - `requires_pre_form: bool`
   - `pre_form: PreFormDefinitionWrite | None` (incluye lista de fields)
5. Al crear una tarea desde un template con `requires_pre_form=true`:
   - Instanciar la subtarea 0 con `subtask_type='pre_form'` (estado inicial `locked` hasta que se genere el link).
   - Auto-generar un `TaskPreFormInstance` con token seguro.
6. Nuevo servicio `task_pre_form_service.py`.
7. Endpoints internos:
   - `POST /tasks/{task_id}/pre-form/generate` — genera o regenera el link
   - `GET /tasks/{task_id}/pre-form/status` — estado y respuestas
8. Endpoints públicos (sin auth):
   - `GET /pre-form/{token}` — devuelve definición + lista de campos
   - `POST /pre-form/{token}` — envía respuesta + archivos (multipart)
9. Al recibir la respuesta del cliente:
   - Marcar `TaskPreFormInstance.submitted_at`
   - Marcar `subtask_type='pre_form'` subtarea como `completed`
   - Desbloquear la siguiente subtarea real

### Frontend — Constructor de formulario en el template

En [`task-template-form-page`](../../microtv-crm-frontend/src/app/features/task-templates/components/task-template-form-page/task-template-form-page.component.ts):

1. Toggle `requiere formulario previo` (slide toggle, `requires_pre_form`).
2. Cuando está activo: mostrar card de constructor con lista de campos.
3. Cada campo tiene: input de label, `<mat-select>` de tipo, toggle requerido, input de placeholder.
4. Botones agregar / eliminar / reordenar campos (drag o flechas).
5. Al guardar el template se serializa `pre_form: { fields: [...] }` en el payload.

### Frontend — Página pública del formulario previo

1. Nueva carpeta `features/pre-form/`.
2. Nueva ruta `pre-form/:token` sin auth guard en [`app.routes.ts`](../../microtv-crm-frontend/src/app/app.routes.ts).
3. `PreFormPageComponent`:
   - Carga definición del formulario desde `GET /pre-form/{token}`.
   - Renderiza campos dinámicamente según `field_type`.
   - Campos FILE: usan el mismo patrón de upload de medios que la `SatisfactionPageComponent`.
   - Al enviar: POST multipart, muestra pantalla de confirmación.

### Frontend — Task execution page

1. Mostrar estado del formulario previo como primer ítem del flujo de subtareas.
2. Botón "Generar link de formulario previo" (admin / ejecutivo).
3. Botón "Regenerar link" si expiró o fue revocado.
4. Sección colapsable con los datos enviados por el cliente una vez completado.

---

## Migraciones — resumen de cambios en DB

| Tabla | Tipo de cambio | Detalle |
|---|---|---|
| `task_comments` | ADD COLUMN | `location_id UUID NULL FK → locations` |
| `tasks` | ADD COLUMN ×4 | `requires_arrival_comment`, `requires_video_evidence`, `arrival_registered_at`, `arrival_comment_id` |
| `task_templates` | ADD COLUMN ×3 | `requires_arrival_comment`, `requires_video_evidence`, `requires_pre_form` |
| `template_subtasks` | ADD COLUMN | `subtask_type VARCHAR(50) DEFAULT 'standard'` |
| `subtasks` | ADD COLUMN | `subtask_type VARCHAR(50) DEFAULT 'standard'` |
| `task_template_pre_forms` | NEW TABLE | `form_id`, `template_id` FK, `title`, `instructions` |
| `task_template_pre_form_fields` | NEW TABLE | `field_id`, `form_id` FK, `label`, `field_type`, `is_required`, `order_index`, `placeholder` |
| `task_pre_form_instances` | NEW TABLE | `instance_id`, `task_id` FK, `token_hash UNIQUE`, `expires_at`, `submitted_at`, `revoked_at`, `created_at` |
| `task_pre_form_responses` | NEW TABLE | `response_id`, `instance_id` FK, `task_id` FK, `submitted_at`, `submitter_ip_hash` |
| `task_pre_form_field_values` | NEW TABLE | `value_id`, `response_id` FK, `field_id` FK, `text_value`, `file_attachment_id` |
| `task_pre_form_attachments` | NEW TABLE | `attachment_id`, `instance_id` FK, `file_name`, `file_url`, `mime_type`, `uploaded_at` |
| `task_satisfaction_forms` | NEW TABLE | Espejo de `ticket_satisfaction_forms` |
| `task_satisfaction_responses` | NEW TABLE | Espejo de `ticket_satisfaction_responses` |

---

## Archivos de referencia clave

| Archivo | Usado como referencia para |
|---|---|
| [`models/ticket.py`](../../microtv-crm-backend/src/crm_backend/models/ticket.py) | Satisfaction forms, arrival flags, comment types |
| [`services/ticket_service.py`](../../microtv-crm-backend/src/crm_backend/services/ticket_service.py) | Lógica de registro de llegada, bloqueo de cierre |
| [`services/ticket_export_service.py`](../../microtv-crm-backend/src/crm_backend/services/ticket_export_service.py) | Exportación PDF |
| [`services/satisfaction_form_service.py`](../../microtv-crm-backend/src/crm_backend/services/satisfaction_form_service.py) | Generación y validación de encuestas |
| [`ticket-execution-page/`](../../microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/) | Patrones de UI: arrivalBanner, comentarios, bloqueos de cierre |
| [`features/satisfaction/`](../../microtv-crm-frontend/src/app/features/satisfaction/) | Página pública de formulario (modelo para pre-form y encuesta de tarea) |

---

## Criterios de verificación

1. Crear un template con `requires_arrival_comment=true`, `requires_pre_form=true` y campos personalizados → verificar que el constructor guarda correctamente.
2. Instanciar una tarea desde ese template → verificar que aparece la subtarea 0 de tipo `pre_form` y se genera el token.
3. Enviar el formulario previo como cliente → verificar que la subtarea 0 pasa a `completed` y la siguiente se desbloquea.
4. Agregar un comentario con ubicación + foto en la tarea → verificar que se registra la llegada y se desbloquea el cierre.
5. Exportar como PDF una tarea completada → verificar comentarios, fotos embebidas y bloque de encuesta.
6. Generar encuesta, enviarla como cliente, ver respuesta en la página de ejecución → verificar flujo completo.
7. Verificar que todos los strings "Tareas" / "Tarea" en la UI muestran "Pedidos" / "Pedido" sin afectar rutas ni APIs.
