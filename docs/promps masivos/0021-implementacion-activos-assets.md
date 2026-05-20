# 0021 — Implementación de Activos (Assets)

## Descripción general

Agregar un sistema completo de gestión de activos físicos al CRM.

Los admins definen **categorías de activos** con campos tipados (`string` | `number`). Los técnicos crean activos por categoría, vinculados a clientes. Los activos se vinculan en relación M:M a tickets y tareas.

El backend usa:
- **Builder pattern** para construir instancias de activos con sus valores de campo.
- **Strategy pattern** para validar los valores de campo según su tipo.

El frontend incorpora:
- Nueva ruta `/assets` con entrada en el sidebar.
- Secciones de vinculación en las páginas de ejecución de ticket y tarea.
- Filtro "buscar por activo" en las páginas de lista de tickets y tareas.

---

## Fase 1 — Esquema de base de datos y modelos backend

### Paso 1 — Crear `models/asset_category.py`
Tabla `asset_categories`:
- `asset_category_id` UUID PK
- `category_name` string único
- `description` string|None
- `is_active` bool
- `created_by_crm_user_id` FK → `crm_users`
- `created_at`, `updated_at`

### Paso 2 — Crear `models/asset_category_field.py`
Tabla `asset_category_fields`:
- `field_id` UUID PK
- `category_id` FK → `asset_categories`
- `field_name` string
- `field_type` string (`"string"` | `"number"`)
- `is_required` bool
- `order_index` int
- `created_at`

Relación: `AssetCategory.fields → list[AssetCategoryField]` (selectin)

### Paso 3 — Crear `models/asset.py`
Tabla `assets`:
- `asset_id` UUID PK
- `category_id` FK → `asset_categories`
- `client_id` FK → `clients`
- `parent_asset_id` FK → `assets` (auto-referencial, nullable) — permite jerarquías como colectivo → monitor
- `asset_name` string
- `notes` string|None
- `created_by_crm_user_id` FK → `crm_users`
- `created_at`, `updated_at`, `deleted_at` (soft delete)

Tabla `asset_field_values`:
- `field_value_id` UUID PK
- `asset_id` FK → `assets`
- `field_id` FK → `asset_category_fields`
- `raw_value` string
- `UniqueConstraint(asset_id, field_id)`

Relaciones: `asset → category (joined)`, `asset → client (joined)`, `asset → parent_asset (joined, nullable)`, `asset → field_values (selectin)`, `field_value → field (joined)`

### Paso 4 — Crear `models/asset_link.py`
Tabla `ticket_assets`:
- `ticket_asset_id` UUID PK
- `ticket_id` FK → `tickets`
- `asset_id` FK → `assets`
- `linked_by_crm_user_id` FK → `crm_users`
- `linked_at` datetime
- `UniqueConstraint(ticket_id, asset_id)`

Tabla `task_assets`:
- Misma estructura para tareas (`task_id` FK → `tasks`)

### Paso 5 — Importar los nuevos modelos
En `db/base.py` (o donde se registra el metadata de SQLAlchemy), importar los cuatro módulos nuevos para que `Base.metadata` los incluya.

### Paso 6 — Extender `db/bootstrap.py`
Agregar los seis nuevos nombres de tabla a la lista en `_ensure_extension_tables`:
```
"asset_categories"
"asset_category_fields"
"assets"
"asset_field_values"
"ticket_assets"
"task_assets"
```
Seguir el patrón existente: `Base.metadata.create_all(bind=bind, tables=missing_tables)`.

Sembrar los nuevos permisos en `_initialize_database_inner` (ver Paso 7).

---

## Fase 2 — Capa de servicio: Builder + Strategy

### Paso 7 — Sembrar permisos en bootstrap
```python
("admin",    "assets.manage_categories", True),
("admin",    "assets.create",            True),
("tecnico",  "assets.create",            True),
("ejecutivo","assets.create",            True),
("admin",    "assets.link",              True),
("tecnico",  "assets.link",              True),
("ejecutivo","assets.link",              True),
("admin",    "assets.edit",              True),
("tecnico",  "assets.edit",              True),   # solo activos propios (ver Step 11)
("ejecutivo","assets.edit",              True),
("admin",    "assets.delete",            True),
("tecnico",  "assets.delete",            False),
("ejecutivo","assets.delete",            False),
```

### Paso 8 — Crear `repositories/asset_repository.py`
Siguiendo el patrón de `TicketRepository`. Métodos:
- `save_category(category)`, `get_category(id)`, `list_categories(is_active=True)`
- `save_asset(asset)`, `get_asset(id)`, `list_assets(client_id=None, category_id=None, search=None)`
- `get_asset_with_links(asset_id)`
- `link_to_ticket(ticket_id, asset_id, actor_user_id)`, `unlink_from_ticket(ticket_id, asset_id)`
- `link_to_task(task_id, asset_id, actor_user_id)`, `unlink_from_task(task_id, asset_id)`
- `list_assets_for_ticket(ticket_id)`, `list_assets_for_task(task_id)`
- `list_tickets_for_asset(asset_id)` → `list[str]` (ticket_ids)
- `list_tasks_for_asset(asset_id)` → `list[str]` (task_ids)

### Paso 9 — Crear `services/assets/strategies.py`
**Strategy pattern** — espeja la implementación en `services/tasks/strategies.py`.

```python
class AssetFieldValueStrategy:
    def validate(self, value: str, field: AssetCategoryField) -> str:
        raise NotImplementedError

class StringFieldValueStrategy(AssetFieldValueStrategy):
    def validate(self, value: str, field: AssetCategoryField) -> str:
        cleaned = value.strip()
        if field.is_required and not cleaned:
            raise AssetValidationError(f"El campo '{field.field_name}' es obligatorio.")
        return cleaned

class NumberFieldValueStrategy(AssetFieldValueStrategy):
    def validate(self, value: str, field: AssetCategoryField) -> str:
        stripped = value.strip()
        if field.is_required and not stripped:
            raise AssetValidationError(f"El campo '{field.field_name}' es obligatorio.")
        if stripped:
            try:
                float(stripped)
            except ValueError:
                raise AssetValidationError(
                    f"El campo '{field.field_name}' debe ser un número. Valor recibido: '{stripped}'."
                )
        return stripped

class AssetFieldValueStrategyRegistry:
    def __init__(self) -> None:
        self._strategies = {
            "string": StringFieldValueStrategy(),
            "number": NumberFieldValueStrategy(),
        }

    def get(self, field_type: str) -> AssetFieldValueStrategy:
        strategy = self._strategies.get(field_type)
        if strategy is None:
            raise AssetValidationError(f"Tipo de campo no soportado: '{field_type}'.")
        return strategy
```

### Paso 10 — Crear `services/assets/builder.py`
**Builder pattern** para construir instancias de `Asset` con sus `AssetFieldValue`.

```python
class AssetBuilder:
    def __init__(self) -> None:
        self._category: AssetCategory | None = None
        self._client_id: str | None = None
        self._parent_asset_id: str | None = None
        self._name: str | None = None
        self._notes: str | None = None
        self._field_values: dict[str, str] = {}  # field_id → validated raw_value

    def with_category(self, category: AssetCategory) -> "AssetBuilder": ...
    def with_client(self, client_id: str) -> "AssetBuilder": ...
    def with_parent_asset(self, asset_id: str | None) -> "AssetBuilder": ...
    def with_name(self, name: str) -> "AssetBuilder": ...
    def with_notes(self, notes: str | None) -> "AssetBuilder": ...

    def with_field_value(
        self,
        field: AssetCategoryField,
        raw_value: str,
        strategy_registry: AssetFieldValueStrategyRegistry,
    ) -> "AssetBuilder":
        strategy = strategy_registry.get(field.field_type)
        validated = strategy.validate(raw_value, field)
        self._field_values[field.field_id] = validated
        return self

    def build(self, actor_crm_user_id: str) -> Asset:
        # Validar campos obligatorios de la categoría
        if self._category is None:
            raise AssetValidationError("La categoría es obligatoria.")
        for field in self._category.fields:
            if field.is_required and not self._field_values.get(field.field_id):
                raise AssetValidationError(f"El campo '{field.field_name}' es obligatorio.")
        # Construir el agregado
        asset = Asset(
            category_id=self._category.asset_category_id,
            client_id=self._client_id,
            parent_asset_id=self._parent_asset_id,
            asset_name=self._name,
            notes=self._notes,
            created_by_crm_user_id=actor_crm_user_id,
        )
        asset.field_values = [
            AssetFieldValue(field_id=fid, raw_value=val)
            for fid, val in self._field_values.items()
        ]
        return asset
```

### Paso 11 — Crear `services/assets/application.py`
`AssetApplicationService` con dependencias inyectadas (asset_repo, client_repo, ticket_repo, task_repo, permission_service, activity_log_service).

Instancia en `__init__`:
```python
self._strategy_registry = AssetFieldValueStrategyRegistry()
```

Métodos principales:
- `list_categories(actor)` → `list[AssetCategory]`
- `create_category(actor, request)` → verifica permiso `assets.manage_categories`
- `list_assets(actor, filters)` → `list[Asset]`
- `get_asset(actor, asset_id)` → `Asset`
- `create_asset(actor, request)` → verifica `assets.create`, usa `AssetBuilder` + registry
- `update_asset(actor, asset_id, request: UpdateAssetRequest)` → verifica `assets.edit`; si el actor tiene rol `tecnico`, además valida que `asset.created_by_crm_user_id == actor.crm_user_id` (solo puede editar los que él creó); admin y ejecutivo pueden editar cualquiera; actualiza campos no-nulos del request y re-valida los `field_values` modificados usando el strategy registry
- `delete_asset(actor, asset_id)` → verifica `assets.delete` (solo admin); aplica soft delete (`deleted_at = now()`); desvincula automáticamente de tickets y tareas antes de marcar como eliminado
- `link_asset_to_ticket(actor, ticket_id, asset_id)` → verifica `assets.link`
- `link_asset_to_task(actor, task_id, asset_id)` → verifica `assets.link`
- `unlink_asset_from_ticket(actor, ticket_id, asset_id)`
- `unlink_asset_from_task(actor, task_id, asset_id)`
- `list_assets_for_ticket(actor, ticket_id)` → `list[Asset]`
- `list_assets_for_task(actor, task_id)` → `list[Asset]`
- `list_tickets_for_asset(actor, asset_id)` → `list[Ticket]`
- `list_tasks_for_asset(actor, asset_id)` → `list[Task]`

---

## Fase 3 — API Endpoints backend

### Paso 12 — Crear `schemas/asset_schemas.py`
**Requests:**
- `CreateAssetCategoryFieldRequest`: field_name, field_type, is_required, order_index
- `CreateAssetCategoryRequest`: category_name, description, fields: list[CreateAssetCategoryFieldRequest]
- `AssetFieldValueRequest`: field_id, value
- `CreateAssetRequest`: category_id, client_id, asset_name, notes, parent_asset_id (optional), field_values: list[AssetFieldValueRequest]
- `UpdateAssetRequest`: asset_name (optional), notes (optional), parent_asset_id (optional), field_values (optional, lista parcial — solo se actualizan los field_ids presentes)
- `LinkAssetRequest`: asset_id

**Responses:**
- `AssetCategoryFieldResponse`: field_id, field_name, field_type, is_required, order_index
- `AssetCategoryResponse`: asset_category_id, category_name, description, is_active, fields: list[AssetCategoryFieldResponse]
- `AssetFieldValueResponse`: field_id, field_name, field_type, raw_value
- `AssetSummaryResponse`: asset_id, asset_name, category_name, client_name, parent_asset_id, parent_asset_name, created_by_crm_user_id
- `AssetResponse`: todos los campos de Summary + field_values: list[AssetFieldValueResponse]

### Paso 13 — Crear `api/endpoints/assets.py`
`router = APIRouter(prefix="/assets", tags=["assets"])`

Todas las rutas usan `actor: ResolvedCrmSession = Depends(get_authenticated_crm_session)` y `asset_service: AssetApplicationService = Depends(get_asset_application_service)`.

| Método | Ruta | Descripción | Permiso |
|--------|------|-------------|---------|
| GET | `/asset-categories` | Listar categorías | autenticado |
| POST | `/asset-categories` | Crear categoría | assets.manage_categories |
| GET | `/asset-categories/{id}/fields` | Campos de una categoría | autenticado |
| GET | `/assets` | Listar activos (query: client_id, category_id, search) | autenticado |
| POST | `/assets` | Crear activo | assets.create |
| GET | `/assets/{id}` | Detalle de activo | autenticado |
| PATCH | `/assets/{id}` | Editar activo | assets.edit + regla de propiedad para tecnico |
| DELETE | `/assets/{id}` | Eliminar activo (soft delete) | assets.delete (solo admin) |
| GET | `/assets/{id}/tickets` | Tickets vinculados (buscar por activo) | autenticado |
| GET | `/assets/{id}/tasks` | Pedidos vinculados (buscar por activo) | autenticado |
| GET | `/tickets/{ticket_id}/assets` | Activos de un ticket | autenticado |
| POST | `/tickets/{ticket_id}/assets` | Vincular activo a ticket | assets.link |
| DELETE | `/tickets/{ticket_id}/assets/{asset_id}` | Desvincular | assets.link |
| GET | `/tasks/{task_id}/assets` | Activos de un pedido | autenticado |
| POST | `/tasks/{task_id}/assets` | Vincular activo a pedido | assets.link |
| DELETE | `/tasks/{task_id}/assets/{asset_id}` | Desvincular | assets.link |

### Paso 14 — Agregar dependencia en `api/dependencies.py`
```python
def get_asset_application_service(session: Session = Depends(get_db_session)) -> AssetApplicationService:
    return AssetApplicationService(
        asset_repository=AssetRepository(session),
        client_repository=ClientRepository(session),
        ticket_repository=TicketRepository(session),
        task_repository=TaskRepository(session),
        permission_service=PermissionService(session),
        activity_log_service=ActivityLogService(session),
    )
```

### Paso 15 — Registrar router en `main.py`
```python
from crm_backend.api.endpoints.assets import router as assets_router
app.include_router(assets_router)
```

---

## Fase 4 — Modelos y servicio frontend

### Paso 16 — Crear `core/models/asset.model.ts`
```typescript
export interface AssetCategoryField {
  field_id: string;
  field_name: string;
  field_type: 'string' | 'number';
  is_required: boolean;
  order_index: number;
}

export interface AssetCategory {
  asset_category_id: string;
  category_name: string;
  description: string | null;
  is_active: boolean;
  fields: AssetCategoryField[];
}

export interface AssetFieldValue {
  field_id: string;
  field_name: string;
  field_type: 'string' | 'number';
  raw_value: string;
}

export interface AssetSummary {
  asset_id: string;
  asset_name: string;
  category_name: string;
  client_name: string;
  parent_asset_id: string | null;
  parent_asset_name: string | null;
  created_by_crm_user_id: string;  // necesario para que el frontend determine si el tecnico puede editar
}

export interface Asset extends AssetSummary {
  category_id: string;
  client_id: string;
  notes: string | null;
  field_values: AssetFieldValue[];
}
```

### Paso 17 — Crear `core/services/asset-management.service.ts`
Injectable, `providedIn: 'root'`, siguiendo el patrón de `TicketManagementService`.

Métodos:
- `listCategories(): Observable<AssetCategory[]>`
- `createCategory(payload): Observable<AssetCategory>`
- `listAssets(filters?: { clientId?, categoryId?, search? }): Observable<AssetSummary[]>`
- `getAsset(assetId): Observable<Asset>`
- `createAsset(payload): Observable<Asset>`
- `updateAsset(assetId: string, payload: UpdateAssetPayload): Observable<Asset>`
- `deleteAsset(assetId: string): Observable<void>`
- `getTicketAssets(ticketId): Observable<AssetSummary[]>`
- `linkAssetToTicket(ticketId, assetId): Observable<void>`
- `unlinkAssetFromTicket(ticketId, assetId): Observable<void>`
- `getTaskAssets(taskId): Observable<AssetSummary[]>`
- `linkAssetToTask(taskId, assetId): Observable<void>`
- `unlinkAssetFromTask(taskId, assetId): Observable<void>`
- `getLinkedTicketsForAsset(assetId): Observable<TicketSummary[]>`
- `getLinkedTasksForAsset(assetId): Observable<TaskSummary[]>`

---

## Fase 5 — Módulo de activos (frontend)

### Estructura de carpetas
```
features/assets/
  components/
    assets-page/
    asset-detail-page/
    create-asset-dialog/
    create-asset-category-dialog/
    asset-vinculation-section/
```

### Paso 18 — `assets-page`
- Standalone, usa `ListingControlsComponent` para búsqueda de texto
- Filtros adicionales: dropdown de categoría, dropdown de cliente
- Tabla/cards de activos: nombre, categoría, cliente, cantidad de tickets/pedidos vinculados
- Botón "Nuevo activo" (visible según permiso `assets.create`)
- Botón "Nueva categoría" solo visible para admin (permiso `assets.manage_categories`)
- En cada fila/card, acciones para **admin**:
  - Ícono ✏️ **Editar** → abre `create-asset-dialog` en modo edición con los datos del activo pre-cargados
  - Ícono 🗑️ **Eliminar** → abre un `MatDialog` de confirmación; al confirmar llama `deleteAsset()`; recarga la lista
- Los técnicos **no** ven botones de edición ni eliminación en esta página

### Paso 19 — `asset-detail-page`
- Card con: nombre, categoría, cliente, activo padre, campo por campo (label: valor)
- Dos tabs Material: "Tickets vinculados" y "Pedidos vinculados"
- Cada tab lista los ítems con: número, título, estado, fecha — click navega a ejecución

### Paso 20 — `create-asset-dialog`
Dialog reutilizable para **creación y edición**. Acepta un input opcional `existingAsset: Asset | null`.

**Modo creación** (`existingAsset === null`):
1. Seleccionar categoría (dropdown carga `listCategories()`) → el form dinámico se genera a partir de los campos de la categoría seleccionada
2. Campos dinámicos: `field_type === 'string'` → `<input matInput type="text">`, `field_type === 'number'` → `<input matInput type="number">`; más: nombre del activo, cliente (requerido), activo padre (opcional, mismo cliente)

Al confirmar: llama `createAsset()`. Si viene de una sección de vinculación con contexto de ticket/tarea, vincula automáticamente tras la creación.

**Modo edición** (`existingAsset !== null`):
- El selector de categoría queda **deshabilitado** (no se puede cambiar la categoría de un activo existente)
- El form se pre-carga con los valores actuales del activo
- El selector de cliente queda **deshabilitado** (no se cambia el cliente del activo)
- Se pueden editar: nombre, notas, activo padre, y todos los `field_values`
- Al confirmar: llama `updateAsset(existingAsset.asset_id, payload)`
- El título del dialog cambia a "Editar activo"

**Control de acceso en el dialog**: si el actor es técnico y `existingAsset.created_by_crm_user_id !== actor.crm_user_id`, el dialog no se abre (la lógica la controla el componente padre antes de abrir el dialog).

### Paso 21 — `create-asset-category-dialog`
Solo accesible para admin.

Form:
- Nombre de categoría, descripción (opcional)
- Lista dinámica de campos: agregar/eliminar filas con nombre + tipo (`string` | `number`) + toggle requerido
- Drag or `order_index` para reordenar (opcional en MVP)

Al confirmar: llama `createCategory()`.

### Paso 22 — `asset-vinculation-section`
Componente reutilizable para ticket-execution-page y task-execution-page.

**Inputs:**
- `ticketId: string | null`
- `taskId: string | null`
- `linkedAssets: AssetSummary[]`
- `disabled: boolean`

**Comportamiento:**
- Lista los activos vinculados como chips/tarjetas con botón de desvincular
- En cada activo vinculado: si `currentUserId === asset.created_by_crm_user_id` **o** el actor es admin, se muestra un ícono ✏️ **Editar** que abre `create-asset-dialog` en modo edición
- Botón **"Vincular activo existente"** → abre dialog de búsqueda/selección de activos existentes (filtra por cliente del ticket/tarea)
- Botón **"Agregar nuevo activo"** → abre `create-asset-dialog` con cliente pre-cargado; al crear, vincula automáticamente
- Emite evento para que el padre recargue los activos

> **Nota técnica:** el `currentUserId` se obtiene de `AuthSessionService.currentUser()` o equivalente. La sección pasa el `asset.created_by_crm_user_id` de cada ítem para comparar sin necesitar una llamada extra.

---

## Fase 6 — Integración en páginas de ejecución y filtros de lista

### Paso 23 — `ticket-execution-page`
- Cargar `ticketAssets` signal: `assetManagementService.getTicketAssets(ticketId)`
- Agregar `<app-asset-vinculation-section>` en el template, después de las secciones existentes (comentarios, adjuntos, inventario)
- Recargar `ticketAssets` en respuesta a eventos del componente hijo

### Paso 24 — `task-execution-page`
- Mismo patrón que el paso anterior usando `taskId`

### Paso 25 — `tickets-page` — filtro "Buscar por activo"
- Agregar un control de selección de activo al panel de filtros (autocomplete o dropdown)
- Cuando el filtro está activo: llamar al backend `GET /assets/{asset_id}/tickets` y mostrar esos tickets
- Limpiar filtro al seleccionar "Todos"

### Paso 26 — `tasks-page` — filtro "Buscar por activo"
- Mismo patrón que el paso anterior para pedidos

---

## Fase 7 — Navegación y rutas

### Paso 27 — `app.routes.ts`
```typescript
{
  path: 'assets',
  canActivate: [authGuard],
  data: { title: 'Activos' },
  loadComponent: () =>
    import('./features/assets/components/assets-page/assets-page.component')
      .then(m => m.AssetsPageComponent)
},
{
  path: 'assets/:assetId',
  canActivate: [authGuard],
  data: { title: 'Activo' },
  loadComponent: () =>
    import('./features/assets/components/asset-detail-page/asset-detail-page.component')
      .then(m => m.AssetDetailPageComponent)
},
```

### Paso 28 — `src/mocks/layout-data.json`
Agregar en la sección "CRM":
```json
{ "id": "assets", "moduleKey": "assets", "label": "Activos", "icon": "devices", "route": "/assets" }
```

### Paso 29 — `core/models/permission.model.ts`
```typescript
export type MockModuleKey =
  | 'dashboard'
  | 'tickets'
  | 'tasks'
  | 'inventory'
  | 'installations'
  | 'clients'
  | 'assets'          // ← nuevo
  | 'billing'
  | 'reports'
  | 'settings'
  | 'profile';
```

### Paso 30 — `mock-access-control.service.ts`
Agregar regla:
```typescript
{ moduleKey: 'assets', allowedRoles: ['admin', 'ejecutivo', 'tecnico'] },
```
El dialog de creación de categorías se controla por el permiso `assets.manage_categories` en el servicio real de permisos (`PermissionService`), no por rol del mock.

---

## Archivos afectados

### Backend — nuevos
| Archivo | Descripción |
|---------|-------------|
| `models/asset_category.py` | Modelos `AssetCategory` + `AssetCategoryField` |
| `models/asset.py` | Modelos `Asset` + `AssetFieldValue` |
| `models/asset_link.py` | Modelos `TicketAsset` + `TaskAsset` |
| `repositories/asset_repository.py` | Capa de acceso a datos |
| `services/assets/__init__.py` | Módulo vacío |
| `services/assets/strategies.py` | Strategy pattern (validación de campos) |
| `services/assets/builder.py` | Builder pattern (construcción de activos) |
| `services/assets/application.py` | Servicio de aplicación principal |
| `schemas/asset_schemas.py` | Schemas Pydantic request/response (incluye `UpdateAssetRequest`) |
| `api/endpoints/assets.py` | Router FastAPI con todos los endpoints |

### Backend — modificados
| Archivo | Cambio |
|---------|--------|
| `db/base.py` | Importar nuevos modelos |
| `db/bootstrap.py` | Agregar tablas + sembrar permisos |
| `api/dependencies.py` | Agregar `get_asset_application_service` |
| `main.py` | Registrar `assets_router` |

### Frontend — nuevos
| Archivo | Descripción |
|---------|-------------|
| `core/models/asset.model.ts` | Interfaces TypeScript |
| `core/services/asset-management.service.ts` | Servicio HTTP |
| `features/assets/components/assets-page/` | 4 archivos (ts, html, scss, spec) |
| `features/assets/components/asset-detail-page/` | 4 archivos |
| `features/assets/components/create-asset-dialog/` | 4 archivos |
| `features/assets/components/create-asset-category-dialog/` | 4 archivos |
| `features/assets/components/asset-vinculation-section/` | 4 archivos |

### Frontend — modificados
| Archivo | Cambio |
|---------|--------|
| `app/app.routes.ts` | Agregar rutas `/assets` y `/assets/:assetId` |
| `src/mocks/layout-data.json` | Agregar ítem de navegación |
| `core/models/permission.model.ts` | Agregar `'assets'` a `MockModuleKey` |
| `core/services/mock-access-control.service.ts` | Agregar regla de módulo assets |
| `ticket-execution-page` | Agregar sección de vinculación de activos |
| `task-execution-page` | Agregar sección de vinculación de activos |
| `tickets-page` | Agregar filtro "buscar por activo" |
| `tasks-page` | Agregar filtro "buscar por activo" |

---

## Verificación

1. `npm run build` en frontend debe pasar con 0 errores tras todos los cambios.
2. Backend: iniciar servidor y verificar ciclo completo:
   - `POST /asset-categories` como admin → crea categoría con campos
   - `POST /assets` como técnico → crea activo usando el builder
   - `POST /tickets/{id}/assets` → vincula activo al ticket
   - `GET /assets/{id}/tickets` → retorna los tickets vinculados
3. Frontend: el sidebar muestra "Activos" para admin/ejecutivo/técnico; oculto para depósito (verificar con el switcher de usuario).
4. La página de ejecución de ticket muestra la sección de vinculación de activos; se puede vincular y desvincular.
5. El dialog "Agregar nuevo activo" genera el formulario dinámico según los campos de la categoría seleccionada.
6. El filtro "Buscar por activo" en tickets-page devuelve solo los tickets vinculados al activo seleccionado.
7. El dialog de creación de categorías es inaccesible para el rol técnico.

---

## Decisiones de diseño

| Decisión | Justificación |
|----------|---------------|
| **Activo padre** (colectivo → monitor) | FK auto-referencial en `assets`, nullable — permite árboles jerárquicos |
| **Valores como `string` en DB** | Los strategies validan/parsean en escritura; no requiere columnas tipadas distintas |
| **Strategy extensible** | Agregar un tipo de campo nuevo (ej. `"date"`) solo requiere una nueva clase de strategy + entrada en el registry |
| **Builder en backend** | Centraliza la lógica de construcción y validación de activos; desacopla el servicio de los detalles de construcción |
| **Filtro "buscar por activo" en backend** | Preferido sobre filtrado en frontend por escalabilidad |

**Fuera del alcance (MVP):** historial de cambios de activos (audit trail de ediciones), importación masiva, códigos QR para activos, edición de categorías/campos ya existentes (solo creación).
