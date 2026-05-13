# Plan: Permission Hardening, Labels UX & Productos Mínimos

## Phase 0 — Etiquetas legibles en el panel de permisos

Actualmente Configuración → Permisos muestra códigos técnicos crudos en la tabla:
`stock.manage`, `ticket.reassign`, `auth_user.create_non_admin`, `admin`, `tecnico`, etc.
Hay que reemplazarlos por texto en español legible para el usuario.

**Archivos afectados:** `permissions-tab.component.ts` y `permissions-tab.component.html`

**Implementación:**

1. `permissions-tab.component.ts` — agregar dos constantes `readonly` en la clase:
   - `PERMISSION_LABELS: Record<string, string>` mapeando cada code a su nombre legible:
     - `stock.manage` → `"Gestión de inventario"`
     - `stock.delete_product` → `"Eliminar productos del inventario"`
     - `ticket.reassign` → `"Reasignar tickets"`
     - `order.reassign` → `"Reasignar pedidos"`
     - `comment.delete` → `"Eliminar comentarios"`
     - `auth_user.create_non_admin` → `"Gestionar usuarios (no administradores)"`
   - `ROLE_LABELS: Record<string, string>` mapeando cada role_key a su nombre legible:
     - `admin` → `"Administrador"`
     - `ejecutivo` → `"Ejecutivo"`
     - `tecnico` → `"Técnico de campo"`
     - `deposito` → `"Encargado de depósito"`
   - Agregar helpers `getPermissionLabel(code: string)` y `getRoleLabel(key: string)` que devuelven el label mapeado o el code como fallback

2. `permissions-tab.component.html` — reemplazar 3 ocurrencias de códigos crudos:
   - L30: `{{ item.permission_code }}` → `{{ getPermissionLabel(item.permission_code) }}`
   - L31: `{{ item.role_key }}` → `{{ getRoleLabel(item.role_key) }}`
   - L57 (sección user overrides): `{{ item.permission_code }}` → `{{ getPermissionLabel(item.permission_code) }}`

**Verificación:** Configuración → Permisos → ver `"Reasignar tickets"` en lugar de `ticket.reassign`, `"Administrador"` en lugar de `admin`.

---

## Phase 1 — Creación de tickets para todos los roles

**Causa raíz:** `ticket_service.py` L101 llama `_ensure_admin_or_executive(actor)` en `create_ticket()`. Los roles `tecnico` y `deposito` reciben 403. El frontend ya muestra el botón "Crear ticket" sin guard para todos los roles.

**Implementación:**

1. `microtv-crm-backend/src/crm_backend/services/ticket_service.py` L101 — eliminar la llamada a `self._ensure_admin_or_executive(actor)` **únicamente** dentro del método `create_ticket()`.
   - **No tocar** los guards en: `list_closed_tickets_for_actor` (L196), `approve_ticket` (L637), `reject_ticket_approval` (L700).
2. Frontend — sin cambios. El botón ya es visible para todos.

**Verificación:** Login como `tecnico` → crear ticket → 200 OK (antes era 403).

---

## Phase 2 — Reasignación sin límite legacy de rol

**Causa raíz:** `tasks/application.py` L1026–1039 usa `{admin, ejecutivo}.intersection(actor.role_keys)` hardcodeado y nunca consulta `PermissionService`. El permiso `ticket.reassign` tampoco está sembrado para `tecnico`/`deposito`.

**Implementación:**

1. **Nueva migración** `microtv-crm-backend/sql/20260513_reassign_permissions_all_roles.sql` — upsert idempotente: insertar `ticket.reassign = TRUE` para roles `tecnico` y `deposito` en `crm_role_permissions`.
2. `microtv-crm-backend/src/crm_backend/db/bootstrap.py` `ROLE_PERMISSION_SEEDS` — agregar las 2 filas nuevas (`tecnico/ticket.reassign` y `deposito/ticket.reassign`) para consistencia con la migración.
3. `microtv-crm-backend/src/crm_backend/services/tasks/application.py` L1026–1039 — reemplazar el check hardcodeado por `PermissionService.resolve(actor.role_keys, crm_user_id, PERMISSION_TICKET_REASSIGN)` (reutilizando la constante ya definida en el módulo).
4. Frontend — `ticket-execution-page.component.ts` `canReassign` ya usa `permissionService.canReassignTickets()` — sin cambios.

**Verificación:** Login como `tecnico` con permiso de reasignación habilitado → intentar reasignar tarea → funciona.

---

## Phase 3 — Ejecutivo: gestión completa de usuarios

**Estado:** La migración `20260513_auth_user_create_non_admin_permission.sql` ya fue aplicada (verificado). El permiso `ejecutivo / auth_user.create_non_admin` existe en DB.

**Bug secundario restante en código:** `permission_service.py` → `update_user_permission()` pasa `_ensure_admin_or_executive()` (ejecutivo debería quedar habilitado) pero tiene un segundo check inmediato que exige `admin` exclusivamente, bloqueando a ejecutivos de editar overrides individuales de permisos.

**Implementación:**

1. `microtv-crm-backend/src/crm_backend/services/permission_service.py` — en `update_user_permission()`, eliminar el segundo check redundante que requiere `admin` explícitamente.
2. Frontend — sin cambios. `settings-page.component.ts` ya maneja ejecutivo correctamente con `canManageAuthUser()` que excluye usuarios admin.

**Verificación:** Login como `ejecutivo` → Configuración → Usuarios → listar, editar, resetear password de usuario no-admin → sin 403.

---

## Phase 4 — Productos mínimos opcionales en creación de ticket y pedido

**Concepto:** Al crear un ticket o pedido, el usuario puede opcionalmente agregar productos del inventario con cantidad. En pedidos, esto es adicional a los materiales heredados del template (que permanecen read-only).

### 4a — DB + Backend

1. **Nueva migración** `microtv-crm-backend/sql/20260513_ticket_required_materials.sql` — crear tabla:
   ```sql
   ticket_required_materials (
     id UUID PK,
     ticket_id UUID FK→tickets ON DELETE CASCADE,
     product_id UUID FK→stock,
     quantity INT NOT NULL CHECK (quantity > 0),
     created_at TIMESTAMPTZ DEFAULT now()
   )
   ```
2. **Nueva migración** `microtv-crm-backend/sql/20260513_task_extra_materials.sql` — crear tabla `task_extra_materials` con misma estructura (FK→tasks).
3. Extender `CreateTicketRequest` — agregar campo opcional `required_materials: list[RequiredMaterialItem] = []` (donde `RequiredMaterialItem` = `{product_id: UUID, quantity: int}`).
4. `ticket_service.create_ticket()` — insertar en `ticket_required_materials` si el payload trae materiales.
5. GET ticket detail — incluir `required_materials` en la respuesta.
6. Extender `CreateTaskRequest` — agregar campo opcional `extra_materials: list[RequiredMaterialItem] = []`.
7. `task_service.create_task()` — insertar en `task_extra_materials` si el payload trae materiales.
8. GET task detail — incluir `extra_materials` en la respuesta.

### 4b — Frontend: creación de ticket

9. `create-ticket-dialog.component.ts` — agregar:
   - Señal `requiredMaterials = signal<{product_id: string, quantity: number}[]>([])`
   - Métodos `addMaterial()` / `removeMaterial(index: number)`
   - Cargar lista de productos via `InventoryService` (ya existente)
   - Incluir `required_materials` en el payload del submit
10. `create-ticket-dialog.component.html` — agregar sección "Materiales requeridos (opcional)":
    - Botón "Agregar material"
    - Lista dinámica: `mat-select` producto + `mat-input` cantidad (type=number) + botón eliminar por fila

### 4c — Frontend: creación de pedido

11. `create-task-dialog.component.html` — la sección de materiales del template (read-only) permanece intacta; agregar debajo un bloque "Materiales adicionales (opcional)" con la misma estructura dinámica.
12. `create-task-dialog.component.ts` — misma lógica con señal `extraMaterials`, `addExtraMaterial()` / `removeExtraMaterial()`. Enviar como `extra_materials` en el payload.

**Verificación:** `npm run build` sin errores. Crear ticket con 2 materiales → verificar filas en DB. Crear pedido con template + extras → verificar en ambas tablas.

---

## Tabla de archivos afectados

| Archivo | Cambio |
|---|---|
| `microtv-crm-frontend/.../permissions-tab/permissions-tab.component.ts` | Agregar `PERMISSION_LABELS`, `ROLE_LABELS`, helpers |
| `microtv-crm-frontend/.../permissions-tab/permissions-tab.component.html` | Reemplazar 3 ocurrencias de código crudo |
| `microtv-crm-backend/src/crm_backend/services/ticket_service.py` | Eliminar guard L101 en `create_ticket()` |
| `microtv-crm-backend/src/crm_backend/services/tasks/application.py` | Reemplazar check hardcodeado L1026–1039 |
| `microtv-crm-backend/src/crm_backend/services/permission_service.py` | Fix segundo check admin en `update_user_permission()` |
| `microtv-crm-backend/src/crm_backend/db/bootstrap.py` | Agregar `tecnico`/`deposito` `ticket.reassign` en seeds |
| `microtv-crm-backend/sql/20260513_reassign_permissions_all_roles.sql` | Nueva migración: `ticket.reassign` para tecnico/deposito |
| `microtv-crm-backend/sql/20260513_ticket_required_materials.sql` | Nueva migración: tabla `ticket_required_materials` |
| `microtv-crm-backend/sql/20260513_task_extra_materials.sql` | Nueva migración: tabla `task_extra_materials` |
| `microtv-crm-frontend/.../create-ticket-dialog/` | Sección materiales opcionales |
| `microtv-crm-frontend/.../create-task-dialog/` | Sección materiales adicionales |

---

## Decisiones de diseño

- **Reassignment vía PermissionService:** se reutiliza el código `ticket.reassign` para tasks también — un solo toggle en el panel de permisos controla ambos módulos.
- **Productos mínimos:** tablas separadas (`ticket_required_materials` y `task_extra_materials`) para mantener independencia entre el módulo de tickets y el de pedidos.
- **No se toca:** guard `adminOnlyGuard` de templates, sidebar inconsistency de deposito/tecnico mostrando "Configuración" (deuda técnica fuera de scope).
- **`auth_micrtv.sql` desactualizado** (faltan migraciones 0008–0010): fuera de scope pero registrado como deuda técnica.
