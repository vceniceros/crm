# 0018 — Permisos unificados, acceso ejecutivo a configuración y registro de actividad

Covers items **1, 2, 7, 8** from `correcciones al crm.md`.

---

## Contexto del sistema (relevado Mayo 2026)

### Estado actual

- `crm_roles`: `role_key` (admin, ejecutivo, tecnico, deposito, dispatcher), `role_label`, `is_active`.
- `crm_user_roles`: tabla M2M usuario↔rol.
- Control de permisos: **hardcodeado** en métodos de servicio (`_ensure_admin`, `_ensure_admin_or_executive`, `_ensure_inventory_admin`, `_ensure_inventory_write_access`).
- La ruta `/settings` ya está protegida por `adminOrExecutiveGuard` en `app.routes.ts`.
- `SettingsService` ya separa correctamente operaciones admin-only vs admin+ejecutivo.
- `_log_activity()` existe en `settings_service.py` pero es un **no-op** (usa raw SQL e ignora silenciosamente si la tabla `activity_log` no existe).
- **No existe tabla `activity_log`.**
- **No existen tablas `crm_role_permissions` ni `crm_user_permissions`.**
- El frontend expone `role_keys` en la sesión; los componentes usan computed signals `isAdmin()`, `isExecutive()` por separado.
- Permisos de stock: roles `deposito`/`admin` hardcodeados en `stock_service.py`.
- Eliminación de comentarios: verificada en `ticket_service.py`, sin tabla de permisos propia.

### Archivos clave — Backend

| Archivo | Rol actual |
|---|---|
| `models/crm_role.py` | Modelo `CrmRole` |
| `models/crm_user_role.py` | M2M `CrmUserRole` |
| `models/settings.py` | `CrmCategory`, `CrmStatus`, `SlaRule`, etc. |
| `services/settings_service.py` | `SettingsService` con `_log_activity()` y guardas de rol |
| `services/stock_service.py` | Guardas de inventario (`_ensure_inventory_write_access`, `_ensure_inventory_admin`) |
| `services/ticket_service.py` | Operaciones sobre tickets y comentarios |
| `services/auth_service.py` | Login, resolución de sesión CRM |
| `api/endpoints/settings.py` | Router `/settings` |
| `api/dependencies.py` | Dependencias FastAPI |

### Archivos clave — Frontend

| Archivo | Rol actual |
|---|---|
| `core/services/auth-session.service.ts` | Estado de sesión global |
| `core/services/settings-management.service.ts` | Llamadas API de configuración |
| `core/models/settings-management.model.ts` | Tipos de configuración |
| `features/settings/components/settings-page/settings-page.component.ts` | Página de configuración |
| `features/settings/components/settings-page/settings-page.component.html` | Template |
| `app.routes.ts` | Guards de ruta |

---

## Fase 1 — Base de datos y modelos SQLAlchemy

### Paso 1 — Nueva migración Alembic

Crear en `microtv-crm-backend/migrations/versions/` con prefijo `20260518_XXXX_permisos_y_log.py`.

**Tabla `crm_role_permissions`**
```sql
CREATE TABLE crm_role_permissions (
    role_permission_id  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_key            VARCHAR(50)  NOT NULL,
    permission_code     VARCHAR(100) NOT NULL,
    is_granted          BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (role_key, permission_code)
);
CREATE INDEX idx_crm_role_permissions_role_key ON crm_role_permissions(role_key);
```

**Tabla `crm_user_permissions`** (overrides por usuario)
```sql
CREATE TABLE crm_user_permissions (
    user_permission_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crm_user_id             UUID        NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE CASCADE,
    permission_code         VARCHAR(100) NOT NULL,
    is_granted              BOOLEAN      NOT NULL DEFAULT TRUE,
    granted_by_crm_user_id  UUID         REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (crm_user_id, permission_code)
);
CREATE INDEX idx_crm_user_permissions_user ON crm_user_permissions(crm_user_id);
```

**Tabla `activity_log`**
```sql
CREATE TABLE activity_log (
    activity_log_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_crm_user_id   UUID         REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    event_code          VARCHAR(100) NOT NULL,
    entity_type         VARCHAR(50),
    entity_id           VARCHAR(36),
    entity_label        VARCHAR(255),
    summary             TEXT,
    payload_json        JSONB        NOT NULL DEFAULT '{}',
    ip_address          VARCHAR(45),
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_activity_log_created_at     ON activity_log(created_at DESC);
CREATE INDEX idx_activity_log_actor          ON activity_log(actor_crm_user_id);
CREATE INDEX idx_activity_log_event_code     ON activity_log(event_code);
CREATE INDEX idx_activity_log_entity         ON activity_log(entity_type, entity_id);
```

**Tabla `activity_log_archive`** (archivado mensual)
```sql
CREATE TABLE activity_log_archive (
    LIKE activity_log INCLUDING ALL,
    archived_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_activity_log_archive_created_at ON activity_log_archive(created_at DESC);
```

**Seeds de permisos por defecto**
```sql
INSERT INTO crm_role_permissions (role_key, permission_code, is_granted) VALUES
  ('admin',    'stock.manage',          TRUE),
  ('admin',    'stock.delete_product',  TRUE),
  ('admin',    'ticket.reassign',       TRUE),
  ('admin',    'order.reassign',        TRUE),
  ('admin',    'comment.delete',        TRUE),
  ('deposito', 'stock.manage',          TRUE),
  ('deposito', 'stock.delete_product',  FALSE),
  ('ejecutivo','ticket.reassign',       TRUE),
  ('ejecutivo','order.reassign',        TRUE)
ON CONFLICT (role_key, permission_code) DO NOTHING;
```

### Paso 2 — Nuevos modelos SQLAlchemy

**Nuevo `models/permission.py`** — clases `RolePermission`, `UserPermission`.

**Nuevo `models/activity_log.py`** — clase `ActivityLog`.

**Actualizar `models/__init__.py`** — exportar `RolePermission`, `UserPermission`, `ActivityLog`.

---

## Fase 2 — Servicios y repositorios backend

Los pasos 3–10 pueden desarrollarse en paralelo una vez completada la Fase 1.

### Paso 3 — Nuevo `PermissionRepository`

Archivo: `repositories/permission_repository.py`

Métodos:
- `get_all_role_permissions() → list[RolePermission]`
- `get_role_permissions(role_key) → list[RolePermission]`
- `get_user_overrides(crm_user_id) → list[UserPermission]`
- `set_role_permission(role_key, permission_code, is_granted, *, actor_id) → RolePermission` (upsert)
- `set_user_permission(crm_user_id, permission_code, is_granted, *, granted_by) → UserPermission` (upsert)
- `delete_user_permission(crm_user_id, permission_code) → None`

### Paso 4 — Nuevo `PermissionService`

Archivo: `services/permission_service.py`

**Códigos de permiso como constantes del módulo:**

| Código | Descripción |
|---|---|
| `stock.manage` | Crear, editar y ajustar stock |
| `stock.delete_product` | Eliminar productos del inventario |
| `ticket.reassign` | Reasignar tickets a cualquier rol |
| `order.reassign` | Reasignar pedidos/solicitudes de depósito |
| `comment.delete` | Eliminar comentarios de otros usuarios |

**Métodos:**
- `resolve(actor_role_keys, crm_user_id, code) → bool`
  - Si `"admin"` está en `actor_role_keys` → siempre `True`.
  - Si hay override de usuario → usar ese valor.
  - Si no → buscar en defaults de rol.
  - Si no hay entrada → `False`.
- `get_effective_permissions(role_keys, crm_user_id) → dict[str, bool]` — mapa completo de todos los códigos conocidos; usado por el endpoint `/me`.
- `update_role_permission(actor, role_key, code, is_granted)` — solo admin.
- `update_user_permission(actor, target_user_id, code, is_granted)` — solo admin; si el actor es ejecutivo, no puede modificar usuarios con rol admin.

### Paso 5 — Nuevo `ActivityLogRepository` + `ActivityLogService`

**`repositories/activity_log_repository.py`**
- `insert(event_code, actor_id, entity_type, entity_id, entity_label, summary, payload_json, ip_address=None) → ActivityLog`
- `list_paginated(filters: ActivityLogFilters) → tuple[list[ActivityLog], int]`

**`services/activity_log_service.py`**
- `log(event_code, actor, *, entity_type=None, entity_id=None, entity_label=None, summary=None, extra=None, ip_address=None) → None`
  - Escribe sincrónicamente dentro de la misma transacción.
  - `ip_address` se pasa solo desde los endpoints de auth; todos los demás pasan `None`.
- `list_for_admin(actor, filters) → tuple[list[ActivityLog], int]`
  - Admin: ve todos los eventos.
  - Ejecutivo: ve todos los eventos excepto los con prefijo `settings.permissions`.

### Paso 6 — Actualizar `settings_service.py`

- Inyectar `ActivityLogService`; reemplazar todos los llamados a `_log_activity()` raw SQL con el servicio.
- Agregar métodos de CRUD de permisos (delegando a `PermissionService`):
  - `list_role_permissions(actor)` — lectura: admin + ejecutivo.
  - `update_role_permission(actor, role_key, code, is_granted)` — escritura: solo admin.
  - `list_user_permissions(actor)` — lectura: admin + ejecutivo.
  - `update_user_permission(actor, user_id, code, is_granted)` — escritura: solo admin.
  - `delete_user_permission(actor, user_id, code)` — escritura: solo admin.
  - `get_effective_permissions_for_user(actor, user_id)` — admin + ejecutivo.

### Paso 7 — Actualizar `stock_service.py`

- Reemplazar `_ensure_inventory_write_access` → `permission_service.resolve(..., "stock.manage")`.
- Reemplazar `_ensure_inventory_admin` → `permission_service.resolve(..., "stock.delete_product")`.
- Agregar llamadas a `activity_log_service.log()`:
  - `stock.product_created` — al crear producto.
  - `stock.product_updated` — al editar producto.
  - `stock.product_deleted` — al eliminar producto.
  - `stock.movement` — en cada movimiento de stock (ajuste, despacho, recepción).

### Paso 8 — Actualizar `ticket_service.py`

- Reemplazar guardas de reasignación hardcodeadas → `permission_service.resolve(..., "ticket.reassign")`.
- Agregar verificación de permiso para eliminar comentarios → `permission_service.resolve(..., "comment.delete")`.
- Edición de comentario propios: **sin cambios**, sigue abierto a todos.
- Agregar llamadas a `activity_log_service.log()`:
  - `ticket.created`, `ticket.status_changed`, `ticket.assigned`, `ticket.reassigned`
  - `ticket.comment_added`, `ticket.comment_deleted`
  - `ticket.closed`, `ticket.reopened`, `ticket.approved`

### Paso 9 — Agregar logs en `auth_service.py` y endpoint de logout

- `auth.login` — en `_resolve_crm_session()` post-login exitoso; pasar `ip_address` desde el endpoint.
- `auth.logout` — en el endpoint de logout; pasar `ip_address` desde el `Request` de FastAPI.

### Paso 10 — Logs adicionales en `settings_service.py`

- `settings.role_updated`, `settings.user_roles_changed`
- `settings.permissions_updated` (role), `settings.user_permission_updated`, `settings.user_permission_deleted`

---

## Fase 3 — Endpoints API backend

### Paso 11 — Nuevos endpoints de permisos en `settings.py`

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| `GET` | `/settings/permissions/roles` | admin + ejecutivo | Lista todos los permisos por rol |
| `PUT` | `/settings/permissions/roles/{role_key}/{permission_code}` | solo admin | Actualiza permiso de rol |
| `GET` | `/settings/permissions/users` | admin + ejecutivo | Lista usuarios con overrides |
| `PUT` | `/settings/permissions/users/{user_id}/{permission_code}` | solo admin | Upsert override de usuario |
| `DELETE` | `/settings/permissions/users/{user_id}/{permission_code}` | solo admin | Elimina override de usuario |
| `GET` | `/settings/permissions/me` | cualquier autenticado | Devuelve `dict[str, bool]` con permisos efectivos del usuario actual |

### Paso 12 — Nuevo endpoint de log de actividad

Archivo: `api/endpoints/activity_log.py`

```
GET /activity-log
  ?user_id=      filtra por actor
  ?event_code=   prefijo del código de evento
  ?entity_type=  filtra por tipo de entidad
  ?date_from=    ISO 8601
  ?date_to=      ISO 8601
  ?page=         default 1
  ?per_page=     default 50, max 200
```

Response: `ActivityLogPageResponse` con `items: list[ActivityLogEntryResponse]` + `total`, `page`, `per_page`.

`ActivityLogEntryResponse`:
```
activity_log_id, actor_crm_user_id, actor_display_name,
event_code, entity_type, entity_id, entity_label,
summary, payload_json, ip_address (solo para admin),
created_at
```

### Paso 13 — Registrar router en `api/router.py`

Incluir el nuevo router de `activity_log`.

### Paso 14 — Nuevos schemas Pydantic

- `schemas/permissions.py` → `RolePermissionResponse`, `UserPermissionOverrideResponse`, `PermissionUpdateRequest`, `EffectivePermissionsResponse`
- `schemas/activity_log.py` → `ActivityLogEntryResponse`, `ActivityLogPageResponse`, `ActivityLogFilters`

---

## Fase 4 — Frontend: modelos y servicios

### Paso 15 — Nuevos tipos en `settings-management.model.ts`

```typescript
SettingsRolePermission         // { role_key, permission_code, is_granted }
SettingsUserPermissionOverride // { crm_user_id, display_name, email, overrides: SettingsRolePermission[] }
SettingsPermissionUpdateRequest// { is_granted: boolean }
SettingsEffectivePermissions   // Record<string, boolean>
ActivityLogEntry               // { activity_log_id, actor_display_name, event_code, entity_type,
                               //   entity_id, entity_label, summary, payload_json, created_at }
ActivityLogFilters             // { userId?, eventCode?, entityType?, dateFrom?, dateTo?, page, perPage }
ActivityLogPage                // { items: ActivityLogEntry[], total, page, perPage }
```

### Paso 16 — Nuevos métodos en `settings-management.service.ts`

```typescript
listRolePermissions(): Observable<SettingsRolePermission[]>
updateRolePermission(roleKey, code, isGranted): Observable<SettingsRolePermission>
listUserPermissionOverrides(): Observable<SettingsUserPermissionOverride[]>
updateUserPermission(userId, code, isGranted): Observable<void>
deleteUserPermission(userId, code): Observable<void>
getMyEffectivePermissions(): Observable<SettingsEffectivePermissions>
listActivityLog(filters: ActivityLogFilters): Observable<ActivityLogPage>
```

### Paso 17 — Nuevo `PermissionService`

Archivo: `core/services/permission.service.ts`

```typescript
@Injectable({ providedIn: 'root' })
export class PermissionService {
  // Signals expuestos
  readonly canManageStock      = signal(false);
  readonly canDeleteProduct    = signal(false);
  readonly canReassignTickets  = signal(false);
  readonly canReassignOrders   = signal(false);
  readonly canDeleteComment    = signal(false);

  refresh(): void  // llama GET /settings/permissions/me y actualiza signals
  clear(): void    // resetea todos a false (logout)
}
```

### Paso 18 — Actualizar `auth-session.service.ts`

- Después de un login exitoso → llamar `PermissionService.refresh()`.
- En `logout()` → llamar `PermissionService.clear()`.

---

## Fase 5 — Frontend: UI de configuración

### Paso 19 — Nuevo componente `PermissionsTabComponent`

Ubicación: `features/settings/components/permissions-tab/`

**Estructura de la UI:**

```
┌─ Permisos y acceso ─────────────────────────────────────────────┐
│                                                                  │
│  [banner si ejecutivo] "Podés ver los permisos pero solo los    │
│  administradores pueden modificarlos."                           │
│                                                                  │
│  ┌── Inventario y Stock ──────────────────────────────────────┐ │
│  │  Gestionar stock          [admin ✓] [deposito ✓] [tecnico ✗]│ │
│  │  "Crear, editar y ajustar cantidades de productos."         │ │
│  │                                                              │ │
│  │  Eliminar productos       [admin ✓] [deposito ✗] [tecnico ✗]│ │
│  │  "Borra permanentemente un producto del inventario."         │ │
│  └──────────────────────────────────────────────────────────── ┘ │
│                                                                  │
│  ┌── Tickets ─────────────────────────────────────────────────┐ │
│  │  Reasignar tickets        [admin ✓] [ejecutivo ✓] ...       │ │
│  └──────────────────────────────────────────────────────────── ┘ │
│                                                                  │
│  ┌── Pedidos de depósito ──────────────────────────────────── ┐ │
│  │  Reasignar pedidos        [admin ✓] [ejecutivo ✓] ...       │ │
│  └──────────────────────────────────────────────────────────── ┘ │
│                                                                  │
│  ┌── Comentarios ──────────────────────────────────────────── ┐ │
│  │  Eliminar comentarios     [admin ✓] [ejecutivo ✗] ...       │ │
│  │  Nota: Editar comentarios propios está disponible para todos │ │
│  └──────────────────────────────────────────────────────────── ┘ │
│                                                                  │
│  ── Overrides por usuario ──────────────────────────────────── │
│  [buscar usuario...] [+ Agregar override]                        │
│  Nombre    Email    Overrides activos    Acciones                │
│  ...        ...     [chip chip]          [editar][eliminar]      │
│                                                                  │
│  [Refrescar permisos]                        (siempre visible)  │
└─────────────────────────────────────────────────────────────── ┘
```

**Notas de implementación:**
- El rol `admin` nunca muestra sus toggles como editables (ni para ejecutivos ni para admins): siempre está marcado y es inmutable en la UI.
- En modo ejecutivo, todos los toggles y botones de escritura están `disabled`; el banner superior explica el motivo.
- El botón "Refrescar permisos" llama a `PermissionService.refresh()` y muestra un snackbar de confirmación.

### Paso 20 — Nuevo componente `ActivityLogTabComponent`

Ubicación: `features/settings/components/activity-log-tab/`

**Columnas de la tabla:**

| Columna | Contenido |
|---|---|
| Fecha y hora | `created_at` formateada localmente |
| Usuario | `actor_display_name` o "Sistema" si null |
| Acción | `event_code` como chip con color por dominio (`auth.*` azul, `ticket.*` verde, `stock.*` naranja, `settings.*` violeta) |
| Entidad | `entity_type` + `entity_label` |
| Resumen | `summary` truncado; expandible al hacer clic en la fila |

**Filtros:**
- Selector de usuario (autocomplete sobre la lista de usuarios activos)
- Dropdown de categoría de evento: Autenticación / Tickets / Stock / Configuración / Todos
- Date range con dos `mat-datepicker`
- Botón "Limpiar filtros"

**Paginación:** `mat-paginator` con opciones 25 / 50 / 100 por página.

**Fila expandible:** al hacer clic, muestra `payload_json` formateado en un `<pre>` con fondo de código. El campo `ip_address` solo aparece si el usuario que consulta es admin.

### Paso 21 — Actualizar `settings-page.component.ts`

- Agregar señales: `rolePermissions`, `userOverrides`, `activityLogPage`.
- Exponer `isAdmin()` computed desde la sesión.
- Agregar tabs: **"Permisos y acceso"** y **"Registro de actividad"**.
- Cargar datos de permisos y log solo cuando el tab correspondiente se activa (lazy, con `(selectedTabChange)`).

### Paso 22 — Actualizar `settings-page.component.html`

Agregar dos `<mat-tab>` nuevos al `<mat-tab-group>` existente, usando los nuevos componentes de tab como hijos.

### Paso 23 — Actualizar componentes con permisos hardcodeados

| Componente | Cambio |
|---|---|
| Lista/form de productos de stock | Mostrar botones de edición/ajuste solo si `permissionService.canManageStock()` |
| Lista de productos de stock | Mostrar botón "Eliminar" solo si `permissionService.canDeleteProduct()` |
| Ticket execution page | Mostrar UI de reasignación solo si `permissionService.canReassignTickets()` |
| Comentarios de ticket | Mostrar botón "Eliminar comentario" solo si `permissionService.canDeleteComment()` |
| Comentarios de ticket | Botón "Editar comentario" propio: **sin cambios**, visible para todos |

---

## Fase 6 — Verificación

- [ ] `npm run build` sin errores de compilación.
- [ ] Backend arranca con la migración aplicada, sin errores.
- [ ] Usuario `admin`: Settings carga, ambas tabs nuevas visibles y editables.
- [ ] Usuario `ejecutivo`: Settings carga, tab "Permisos y acceso" visible en modo solo lectura (banner explicativo), tab "Registro de actividad" visible.
- [ ] Usuario `tecnico` o `deposito`: ruta `/settings` bloqueada por guard (comportamiento sin cambios).
- [ ] Quitar permiso `stock.manage` a un usuario `deposito` → operaciones de stock devuelven 403.
- [ ] Dar override `stock.manage` a un usuario `tecnico` → ese usuario puede escribir stock.
- [ ] Log de actividad se popula tras: login, cambio de estado de ticket, movimiento de stock, cambio de permisos.
- [ ] `ip_address` visible en filas de `auth.login` / `auth.logout`; ausente en filas de otros eventos.
- [ ] Botón "Eliminar comentario" oculto para usuarios sin permiso `comment.delete`; botón "Editar" sigue visible.
- [ ] Refrescar permisos desde la UI actualiza los signals sin requerir re-login.

---

## Archivos afectados

### Backend — Nuevos

```
microtv-crm-backend/migrations/versions/20260518_XXXX_permisos_y_log.py
microtv-crm-backend/src/crm_backend/models/permission.py
microtv-crm-backend/src/crm_backend/models/activity_log.py
microtv-crm-backend/src/crm_backend/repositories/permission_repository.py
microtv-crm-backend/src/crm_backend/repositories/activity_log_repository.py
microtv-crm-backend/src/crm_backend/services/permission_service.py
microtv-crm-backend/src/crm_backend/services/activity_log_service.py
microtv-crm-backend/src/crm_backend/schemas/permissions.py
microtv-crm-backend/src/crm_backend/schemas/activity_log.py
microtv-crm-backend/src/crm_backend/api/endpoints/activity_log.py
```

### Backend — Modificados

```
microtv-crm-backend/src/crm_backend/models/__init__.py
microtv-crm-backend/src/crm_backend/repositories/__init__.py
microtv-crm-backend/src/crm_backend/services/__init__.py
microtv-crm-backend/src/crm_backend/services/settings_service.py
microtv-crm-backend/src/crm_backend/services/stock_service.py
microtv-crm-backend/src/crm_backend/services/ticket_service.py
microtv-crm-backend/src/crm_backend/services/auth_service.py
microtv-crm-backend/src/crm_backend/api/endpoints/settings.py
microtv-crm-backend/src/crm_backend/api/router.py
microtv-crm-backend/src/crm_backend/api/dependencies.py
```

### Frontend — Nuevos

```
microtv-crm-frontend/src/app/core/services/permission.service.ts
microtv-crm-frontend/src/app/features/settings/components/permissions-tab/permissions-tab.component.ts
microtv-crm-frontend/src/app/features/settings/components/permissions-tab/permissions-tab.component.html
microtv-crm-frontend/src/app/features/settings/components/permissions-tab/permissions-tab.component.scss
microtv-crm-frontend/src/app/features/settings/components/activity-log-tab/activity-log-tab.component.ts
microtv-crm-frontend/src/app/features/settings/components/activity-log-tab/activity-log-tab.component.html
microtv-crm-frontend/src/app/features/settings/components/activity-log-tab/activity-log-tab.component.scss
```

### Frontend — Modificados

```
microtv-crm-frontend/src/app/core/models/settings-management.model.ts
microtv-crm-frontend/src/app/core/services/settings-management.service.ts
microtv-crm-frontend/src/app/core/services/auth-session.service.ts
microtv-crm-frontend/src/app/features/settings/components/settings-page/settings-page.component.ts
microtv-crm-frontend/src/app/features/settings/components/settings-page/settings-page.component.html
```

Y los componentes de stock y tickets con permisos hardcodeados (identificar con grep sobre `isAdmin()`, `isExecutive()`, `_ensure_inventory_admin` antes de implementar).

---

## Decisiones de diseño

| Decisión | Detalle |
|---|---|
| `is_granted BOOL` en ambas tablas | Soporta deny explícito en el futuro sin cambio de esquema |
| Escritura de log sincrónica | En la misma transacción DB; sin cola async. Suficiente para esta escala |
| Resolución de permisos | `user override → role default → deny`. El rol `admin` siempre `True` sin consulta |
| Ejecutivo no puede modificar permisos de admin | Aplicado en `PermissionService.update_user_permission()` en el backend; reflejo visual en frontend |
| Edición de comentario abierta a todos | Sin cambios; solo la eliminación queda bajo permiso `comment.delete` |
| `stock.manage` vs `stock.delete_product` | Son dos permisos separados: gestión cubre crear/editar/ajustar; eliminación es un permiso distinto más restrictivo |
| Dos códigos de reasignación | `ticket.reassign` y `order.reassign` son independientes para granularidad |
| Refresh de permisos en UI | El frontend llama `PermissionService.refresh()` tras cualquier escritura exitosa de permiso. La tab de permisos muestra siempre un botón "Refrescar permisos" para sesiones desactualizadas |
| Archivado mensual del log | Tarea programada (APScheduler o cron interno) que mueve filas con `created_at < NOW() - 90 days` de `activity_log` a `activity_log_archive`. La UI solo consulta la tabla viva. El archivo es accesible vía DB directamente en v1 |
| IP address solo en auth events | `ip_address` se pasa al `ActivityLogService` únicamente desde los endpoints de `auth.login` y `auth.logout` usando el objeto `Request` de FastAPI. Todos los demás servicios pasan `ip_address=None`. El campo se oculta en la UI para ejecutivos |
