# 0014 — Implementación Completa de Notificaciones

## Contexto y Diagnóstico

El sistema de notificaciones existe parcialmente pero falla de forma intermitente en producción. Existen **tres causas raíz**:

### Causa 1 — Migración rota bloquea el sistema

`20260428_notifications_seed.sql` inserta en la tabla `crm_notification_rules`, pero esa tabla **no tiene `CREATE TABLE` en ningún archivo SQL**. `migrate_prod.sh` sólo ignora errores de "ya existe" — un error de "tabla no existe" es una falla dura que puede dejar la migración sin ejecutarse o cortar la cadena de migraciones posteriores.

**Fix:** Crear `20260511_notification_rules_ddl.sql` con el `CREATE TABLE IF NOT EXISTS` correspondiente, antes del seed.

### Causa 2 — Hooks de negocio faltantes

La mayoría de las notificaciones requeridas no tienen ningún trigger en el backend. Las siguientes rutas de negocio no disparan nada:

- Cliente completa el formulario previo (`task_pre_form_service.py`)
- Cliente responde encuesta de satisfacción (`satisfaction_form_service.py` y `task_satisfaction_form_service.py`)
- Stock bajo o sin stock (`stock_service.py`)
- Ticket o subtarea sin asignar al crearse
- Pedido asignado a nivel de tarea (sólo subtareas tienen notify hoy)
- Solicitud de depósito aprobada pendiente de despacho
- Productos ya instalados/recibidos (además del flujo existente al requester)

### Causa 3 — Servicios construidos sin `NotificationService` inyectado

En `dependencies.py`, cuatro factories construyen sus servicios **sin** pasarles `NotificationService`, lo que los hace físicamente incapaces de notificar aunque se agregue el código:

| Factory | Servicio |
|---|---|
| `get_task_pre_form_service` | `TaskPreFormService` |
| `get_satisfaction_form_service` | `PublicSatisfactionFormService` |
| `get_task_satisfaction_form_service` | `TaskSatisfactionFormService` |
| `get_stock_application_service` | `StockApplicationService` |

---

## Notificaciones Requeridas

### Ejecutivo
| Evento | Tipo | Nota |
|---|---|---|
| Cliente completó el formulario previo del pedido `#N` | `task_pre_form_completed` | |
| Pedido asignado | `task_assigned` | |
| Ticket espera su aprobación | `ticket_pending_approval` | **Ya existe** |
| Pedido espera su aprobación | `task_pending_approval` | **Ya existe** |
| Cliente respondió la encuesta del ticket | `ticket_satisfaction_submitted` | |
| Cliente respondió la encuesta del pedido | `task_satisfaction_submitted` | |

### Depósito (`encargado_deposito`)
| Evento | Tipo | Nota |
|---|---|---|
| Solicitud a depósito realizada | `deposit_request_created` | **Ya existe** |
| Productos esperan despacho | `deposit_pending_dispatch` | |
| Productos ya despachados | `deposit_request_dispatched` | **Ya existe** (al requester) |
| Productos ya instalados | `deposit_products_installed` | |
| Producto `<código>` cerca de quedarse sin stock (< 3 unidades) | `stock_low` | |
| Producto `<código>` sin stock | `stock_out` | |

### Técnico de campo (`tecnico_campo`)
| Evento | Tipo | Nota |
|---|---|---|
| Material despachado para tu ticket `#N` | `deposit_request_dispatched` | **Ya existe** |
| Material despachado para tu pedido `#N` | `deposit_request_dispatched` | **Ya existe** |
| Ticket aprobado | `ticket_approved` | **Ya existe** |
| Pedido aprobado | `task_approved` | **Ya existe** |
| Cliente respondió la encuesta del ticket que cerraste | `ticket_satisfaction_submitted` | |
| Cliente respondió la encuesta del pedido que cerraste | `task_satisfaction_submitted` | |

### Todos los roles
| Evento | Tipo | Nota |
|---|---|---|
| Se te asignó un ticket | `ticket_assigned` | **Ya existe** |
| Se te asignó un pedido | `task_assigned` | **Falta** |
| Ticket sin asignar en tu rol | `ticket_unassigned_in_role` | |
| Pedido / subtarea sin asignar en tu rol | `task_unassigned_in_role` | |

> **Regla general:** toda notificación que mencione "ticket/pedido" son **dos notificaciones separadas**, una por tipo de entidad.

---

## Fase 1 — Diagnóstico y Reparación de Migración

### Paso 1 — Auditar estado actual en lab

```sql
SELECT migration_name, applied_at
FROM crm_schema_migrations
ORDER BY applied_at;
```

Confirmar:
- `20260423_crm_notifications.sql` está registrada
- `20260428_notifications_seed.sql` está registrada o fallida
- Identificar si existe la tabla `crm_notification_rules` en el esquema actual

### Paso 2 — Crear archivo de migración DDL

**Archivo:** `microtv-crm-backend/sql/20260511_notification_rules_ddl.sql`

```sql
-- DDL para tabla de reglas de notificación
-- Necesaria para que 20260428_notifications_seed.sql pueda ejecutarse sin error
-- Fecha: 2026-05-11

CREATE TABLE IF NOT EXISTS crm_notification_rules (
    notification_rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_code           TEXT NOT NULL UNIQUE,
    label                TEXT NOT NULL,
    notify_assigned      BOOLEAN NOT NULL DEFAULT TRUE,
    notify_roles_json    JSONB NOT NULL DEFAULT '[]',
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

`migrate_prod.sh` toma todos los `*.sql` del directorio en orden alfabético, por lo que `20260511_*` se aplica antes del seed (que es `20260428_*`, ya registrado o que reintenta si no lo está). Si el seed ya fue registrado como aplicado pero la tabla no existe, re-ejecutar el seed manualmente una sola vez.

---

## Fase 2 — Modelo: Nuevos Tipos de Notificación

**Archivo:** `microtv-crm-backend/src/crm_backend/models/notification.py`

### Agregar a `NotificationType`

```python
# Asignación de pedido
TASK_ASSIGNED = "task_assigned"

# Formularios de cliente
TASK_PRE_FORM_COMPLETED = "task_pre_form_completed"
TICKET_SATISFACTION_SUBMITTED = "ticket_satisfaction_submitted"
TASK_SATISFACTION_SUBMITTED = "task_satisfaction_submitted"

# Stock
STOCK_LOW = "stock_low"
STOCK_OUT = "stock_out"

# Sin asignar
TICKET_UNASSIGNED_IN_ROLE = "ticket_unassigned_in_role"
TASK_UNASSIGNED_IN_ROLE = "task_unassigned_in_role"

# Depósito
DEPOSIT_PENDING_DISPATCH = "deposit_pending_dispatch"
DEPOSIT_PRODUCTS_INSTALLED = "deposit_products_installed"
```

### Agregar a `NotificationEntityType`

```python
STOCK_PRODUCT = "stock_product"
```

---

## Fase 3 — Hooks de Negocio en Servicios

### 3.1 `tasks/application.py` — `TaskApplicationService`

**Dónde:** `create_task()` después de persistir la tarea.

**Lógica:**
- Si el primer subtask tiene `assigned_crm_user_id` → `notify(TASK_ASSIGNED)` al asignado + `notify_bulk(TASK_ASSIGNED)` a todos los ejecutivos
- Si el primer subtask entra en `PENDING_ASSIGNMENT` → `notify_bulk(TASK_UNASSIGNED_IN_ROLE)` a los usuarios cuyo rol coincida con `subtask.responsible_role_key`

**También:** cuando `_advance_to_next_subtask()` (o lógica equivalente de unlock) deja un subtask en `PENDING_ASSIGNMENT` → misma notificación bulk por rol.

---

### 3.2 `ticket_service.py` — `TicketApplicationService`

**Dónde:** `create_ticket()` después de guardar.

**Lógica:**
- Si `ticket.assigned_user_id is None` → `notify_bulk(TICKET_UNASSIGNED_IN_ROLE)` a todos los usuarios con rol `tecnico_campo`
- Si en el flujo de reasignación el ticket queda sin asignar → misma notificación

---

### 3.3 `task_pre_form_service.py` — `TaskPreFormService`

**Constructor:** agregar `notification_service: NotificationService | None = None` y `user_repository: CrmUserRepository | None = None`.

**Dónde:** `submit_response()` después de `_mark_pre_form_subtask_completed()`.

**Lógica:**
```python
if self._notification_service and self._user_repository:
    ejecutivo_ids = self._user_repository.get_user_ids_by_role_key("ejecutivo")
    task_number = getattr(instance.task, "task_number", instance.task.task_id[:8])
    self._notification_service.notify_bulk(
        recipient_crm_user_ids=ejecutivo_ids,
        notification_type=NotificationType.TASK_PRE_FORM_COMPLETED,
        title=f"Cliente completó el formulario previo del pedido #{task_number}",
        body="El cliente completó el formulario previo. El pedido puede continuar.",
        entity_type=NotificationEntityType.TASK,
        entity_id=instance.task.task_id,
    )
```

---

### 3.4 `satisfaction_form_service.py` — `PublicSatisfactionFormService`

**Constructor:** agregar `notification_service: NotificationService | None = None`, `user_repository: CrmUserRepository | None = None`.

**Dónde:** `submit_response()` después del `commit()`.

**Lógica:**
```python
if self._notification_service and self._user_repository:
    ticket = form.ticket  # relación ya cargada
    # Notificar al técnico que cerró el ticket
    if ticket.resolved_by_crm_user_id:
        self._notification_service.notify(
            recipient_crm_user_id=ticket.resolved_by_crm_user_id,
            notification_type=NotificationType.TICKET_SATISFACTION_SUBMITTED,
            title=f"El cliente respondió la encuesta del ticket #{ticket.ticket_number}",
            body=f"Puntuación: {response.rating}/5",
            entity_type=NotificationEntityType.TICKET,
            entity_id=ticket.ticket_id,
        )
    # Notificar a todos los ejecutivos
    ejecutivo_ids = self._user_repository.get_user_ids_by_role_key("ejecutivo")
    self._notification_service.notify_bulk(
        recipient_crm_user_ids=ejecutivo_ids,
        notification_type=NotificationType.TICKET_SATISFACTION_SUBMITTED,
        title=f"El cliente respondió la encuesta del ticket #{ticket.ticket_number}",
        body=f"Puntuación: {response.rating}/5",
        entity_type=NotificationEntityType.TICKET,
        entity_id=ticket.ticket_id,
    )
```

---

### 3.5 `task_satisfaction_form_service.py` — `TaskSatisfactionFormService`

**Constructor:** agregar `notification_service: NotificationService | None = None`, `user_repository: CrmUserRepository | None = None`.

**Dónde:** `submit_response()` después del `commit()`.

**Lógica:** igual que 3.4 pero con `TASK_SATISFACTION_SUBMITTED`, `entity_type=TASK`, y notificando al `task.current_assigned_crm_user_id`.

---

### 3.6 `material_flow_service.py` — `InventoryRequestFacade`

> Ya tiene `notification_service` inyectado. Sólo faltan dos puntos de disparo.

**Punto A — Solicitud aprobada, pendiente de despacho:**

Después de aprobar la solicitud (estado cambia a `APPROVED` o equivalente), donde ya se tienen los `deposito_user_ids`:

```python
self._notification_service.notify_bulk(
    recipient_crm_user_ids=list(set(deposito_user_ids) - {actor.crm_user.crm_user_id}),
    notification_type=NotificationType.DEPOSIT_PENDING_DISPATCH,
    title="Hay materiales esperando despacho",
    body="Una solicitud fue aprobada y está lista para ser despachada desde el depósito.",
    entity_type=NotificationEntityType.DEPOSIT_REQUEST,
    entity_id=persisted_request.request_id,
)
```

**Punto B — Recepción confirmada (productos instalados):**

En el path de `DEPOSIT_REQUEST_RECEIVED`, después de notificar al requester, agregar:

```python
deposito_ids = self._user_repository.get_user_ids_by_role_key("encargado_deposito")
self._notification_service.notify_bulk(
    recipient_crm_user_ids=deposito_ids,
    notification_type=NotificationType.DEPOSIT_PRODUCTS_INSTALLED,
    title="Materiales confirmados como recibidos/instalados",
    body="El técnico confirmó la recepción de los materiales de la solicitud.",
    entity_type=NotificationEntityType.DEPOSIT_REQUEST,
    entity_id=linked_request.request_id,
)
```

---

### 3.7 `stock_service.py` — `StockApplicationService`

**Constructor:** agregar `notification_service: NotificationService | None = None`, `user_repository: CrmUserRepository | None = None`.

**Dónde:** `decrease_stock()` después de `_product_repository.save(product)`.

**Lógica (verificar OUT primero para evitar doble disparo):**
```python
if self._notification_service and self._user_repository:
    stock_now = product.current_stock
    if stock_now == 0:
        notif_type = NotificationType.STOCK_OUT
        title = f"Sin stock: {product.visible_product_code}"
        body = f"El producto '{product.product_name}' llegó a 0 unidades."
    elif stock_now < 3:
        notif_type = NotificationType.STOCK_LOW
        title = f"Stock bajo: {product.visible_product_code} ({stock_now} unidades)"
        body = f"El producto '{product.product_name}' tiene menos de 3 unidades disponibles."
    else:
        notif_type = None

    if notif_type:
        deposito_ids = self._user_repository.get_user_ids_by_role_key("encargado_deposito")
        ejecutivo_ids = self._user_repository.get_user_ids_by_role_key("ejecutivo")
        recipient_ids = list(set(deposito_ids + ejecutivo_ids))
        self._notification_service.notify_bulk(
            recipient_crm_user_ids=recipient_ids,
            notification_type=notif_type,
            title=title,
            body=body,
            entity_type=NotificationEntityType.STOCK_PRODUCT,
            entity_id=product.product_id,
        )
```

---

## Fase 4 — Wiring en `dependencies.py`

**Archivo:** `microtv-crm-backend/src/crm_backend/api/dependencies.py`

Actualizar las cuatro factories para inyectar `NotificationService` y `CrmUserRepository`:

### `get_task_pre_form_service`
```python
def get_task_pre_form_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    notification_service: NotificationService = Depends(get_notification_service),
    user_repository: CrmUserRepository = Depends(get_crm_user_repository),
) -> TaskPreFormService:
    return TaskPreFormService(
        session=session,
        expiry_hours=settings.satisfaction_form_expiry_hours,
        notification_service=notification_service,
        user_repository=user_repository,
    )
```

### `get_satisfaction_form_service`
```python
def get_satisfaction_form_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    notification_service: NotificationService = Depends(get_notification_service),
    user_repository: CrmUserRepository = Depends(get_crm_user_repository),
) -> PublicSatisfactionFormService:
    return PublicSatisfactionFormService(
        session=session,
        # ... parámetros existentes ...
        notification_service=notification_service,
        user_repository=user_repository,
    )
```

### `get_task_satisfaction_form_service`
```python
def get_task_satisfaction_form_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    notification_service: NotificationService = Depends(get_notification_service),
    user_repository: CrmUserRepository = Depends(get_crm_user_repository),
) -> TaskSatisfactionFormService:
    return TaskSatisfactionFormService(
        session=session,
        expiry_hours=settings.satisfaction_form_expiry_hours,
        notification_service=notification_service,
        user_repository=user_repository,
    )
```

### `get_stock_application_service`
```python
def get_stock_application_service(
    settings: Settings = Depends(get_settings),
    category_repository: StockCategoryRepository = Depends(get_stock_category_repository),
    product_repository: StockProductRepository = Depends(get_stock_product_repository),
    notification_service: NotificationService = Depends(get_notification_service),
    user_repository: CrmUserRepository = Depends(get_crm_user_repository),
) -> StockApplicationService:
    return StockApplicationService(
        settings,
        category_repository,
        product_repository,
        notification_service=notification_service,
        user_repository=user_repository,
    )
```

---

## Fase 5 — Frontend: Nuevos Tipos y Routing

### 5.1 Modelo

**Archivo:** `microtv-crm-frontend/src/app/core/models/notification.model.ts`

Agregar las constantes de tipo para los 10 nuevos tipos.

### 5.2 Routing en topbar

**Archivo:** `microtv-crm-frontend/src/app/layout/components/topbar/topbar.component.ts`

Extender el método `openNotification()` con los casos adicionales:

| Tipo | Ruta destino |
|---|---|
| `task_assigned` | `/pedidos/{entity_id}` |
| `task_pre_form_completed` | `/pedidos/{entity_id}` |
| `task_satisfaction_submitted` | `/pedidos/{entity_id}` |
| `task_unassigned_in_role` | `/pedidos` (lista, sin entity_id) |
| `ticket_satisfaction_submitted` | `/tickets/{entity_id}` |
| `ticket_unassigned_in_role` | `/tickets` (lista, sin entity_id) |
| `stock_low` / `stock_out` | `/deposito/productos/{entity_id}` |
| `deposit_pending_dispatch` | `/deposito/solicitudes/{entity_id}` |
| `deposit_products_installed` | `/deposito/solicitudes/{entity_id}` |

---

## Verificación en Laboratorio

1. **Auditar migraciones:** `SELECT migration_name FROM crm_schema_migrations ORDER BY migration_name;`
2. **Ejecutar migración nueva:** `./sql/migrate_prod.sh` — confirmar que `20260511_notification_rules_ddl.sql` y `20260428_notifications_seed.sql` aplican sin errores
3. **Formulario previo:** POST a endpoint público de pre-form con token válido → ejecutivos reciben `task_pre_form_completed` en el bell
4. **Encuesta ticket:** Cerrar ticket → generar y enviar encuesta de satisfacción → técnico + ejecutivos reciben `ticket_satisfaction_submitted`
5. **Encuesta pedido:** Ídem para un pedido/tarea
6. **Stock bajo:** Bajar stock de un producto a 2 → `stock_low` llega a deposito + ejecutivos; bajar a 0 → `stock_out`
7. **Ticket sin asignar:** Crear ticket sin asignado → técnicos de campo reciben `ticket_unassigned_in_role`
8. **Pedido sin asignar:** Crear pedido sin responsable por defecto → usuarios del rol correspondiente reciben `task_unassigned_in_role`
9. **Despacho pendiente:** Aprobar solicitud de depósito → deposito recibe `deposit_pending_dispatch`
10. **Instalado:** Técnico confirma recepción → deposito recibe `deposit_products_installed`
11. **Frontend routing:** Click en cada tipo de notificación → navega a la página correcta
12. **Deploy a prod:** Ejecutar `migrate_prod.sh`, smoke-test de al menos un evento por tipo

---

## Decisiones de Diseño

- Todos los nuevos parámetros en constructores son `... | None = None` — sin breaking changes para tests existentes
- El chequeo de stock sigue el orden `== 0 → STOCK_OUT`, `< 3 → STOCK_LOW` para evitar doble disparo en el mismo evento
- La tabla `crm_notification_rules` se crea únicamente para desbloquear el seed; la lógica de disparo de notificaciones sigue siendo code-driven
- El polling del frontend es de 30 segundos (`POLL_INTERVAL_MS = 30_000`) — suficiente para todos estos casos de uso operativos
