# Fix producción: solicitud depósito, reasignación cruzada, 500 reject_close, historial cerrados

## Resumen

Cuatro bugs encontrados en producción:

| # | Descripción | Impacto |
|---|---|---|
| Bug 1a | Botón "Hacer solicitud a depósito" deshabilitado para rol `deposito` y otros roles | El usuario que opera el ticket no puede crear la solicitud |
| Bug 1b | Al despachar una solicitud, `quantity_available` del producto **aumenta** en lugar de disminuir | El inventario queda inconsistente |
| Bug 2 | `deposito` no puede reasignar tickets a `tecnico` ni viceversa | Bloquea el flujo operativo entre roles |
| Bug 3 | `POST /tickets/{id}/reject` lanza 500 (`ForeignKeyViolation`) siempre que el ejecutivo rechaza el cierre de un ticket | La acción falla completamente en producción |
| Bug 4 | Los tickets cerrados desaparecen del historial para cualquier rol que no sea `admin` o `ejecutivo` | Los técnicos y depósito no pueden consultar su propio historial |

---

## Bug 1a — Botón "Hacer solicitud" no disponible para todos los roles

### Diagnóstico

**Frontend** — `ticket-execution-page.component.ts` línea 201:
```typescript
readonly canCreateInventoryRequest = computed(() =>
  this.canOperateTicket() && (this.isTecnico() || this.isAdmin())
);
```
La condición filtra explícitamente por rol, impidiendo que `deposito`, `ejecutivo` u otros roles que tengan el ticket asignado puedan ver el botón.

**Backend** — `material_flow_service.py` líneas 731–734:
```python
def _ensure_request_create_access(self, actor: ResolvedCrmSession) -> None:
    if "admin" in actor.role_keys or "tecnico" in actor.role_keys:
        return
    raise InventoryAccessDeniedError("Solo un técnico o administrador puede crear solicitudes adicionales.")
```
Bloquea a `deposito` y `ejecutivo` en el servidor también.

`canOperateTicket()` ya valida que el usuario sea el asignado actual (por usuario o por rol), por lo que restringir por tipo de rol encima es redundante y erróneo.

### Solución

**Paso 1 — Frontend** `ticket-execution-page.component.ts` L201

```typescript
// Antes
readonly canCreateInventoryRequest = computed(() =>
  this.canOperateTicket() && (this.isTecnico() || this.isAdmin())
);

// Después
readonly canCreateInventoryRequest = computed(() => this.canOperateTicket());
```

**Paso 2 — Backend** `material_flow_service.py` L731–734

```python
# Antes
def _ensure_request_create_access(self, actor: ResolvedCrmSession) -> None:
    if "admin" in actor.role_keys or "tecnico" in actor.role_keys:
        return
    raise InventoryAccessDeniedError("Solo un técnico o administrador puede crear solicitudes adicionales.")

# Después
def _ensure_request_create_access(self, actor: ResolvedCrmSession) -> None:
    if not actor.role_keys:
        raise InventoryAccessDeniedError("El usuario no tiene roles asignados.")
    # La validación de acceso al ticket específico la realiza _ensure_ticket_is_operable_by_actor
```

> El control de acceso real ya lo ejerce `_ensure_ticket_is_operable_by_actor` (línea 485), que comprueba que el actor sea el asignado actual al ticket. No se pierde seguridad.

> **Nota:** el input numérico de cantidad ya existe tanto en el formulario de solicitud como en el de despacho — no requiere cambios de UI.

---

## Bug 1b — Stock aumenta en lugar de disminuir al despachar

### Diagnóstico

**Backend** — `material_flow_service.py` `_populate_dispatch_items` línea 346:
```python
product.increase_stock(          # ← BUG: debería ser decrease_stock
    quantity=item_payload.quantity_dispatched,
    actor_crm_user_id=actor.crm_user.crm_user_id,
    warehouse_id=warehouse_id,
    reference_entity_type=reference_entity_type,
    reference_entity_id=dispatch.dispatch_id,
    notes=...,
)
```
Este método es llamado tanto para despachos de tickets como de tareas (`_task_material_flow._populate_dispatch_items`). Ambos flujos están afectados.

### Solución

**Paso 3 — Backend** `material_flow_service.py` L346

```python
# Antes
product.increase_stock(
    quantity=item_payload.quantity_dispatched,
    ...
)

# Después
product.decrease_stock(
    quantity=item_payload.quantity_dispatched,
    ...
)
```

---

## Bug 2 — Reasignación cruzada deposito ↔ tecnico bloqueada

### Diagnóstico

**Backend** — `ticket_service.py` `list_assignable_roles` líneas 222–227:
```python
actor_role_ids = self._actor_role_ids(actor)
if {"tecnico", "deposito"}.intersection(actor_role_keys):
    for role in roles:
        if self._normalize_role_key(role.role_key) == "admin":
            actor_role_ids.add(role.crm_role_id)          # solo agrega admin
return [role for role in roles if role.crm_role_id in actor_role_ids]
```
Un `deposito` solo puede ver su propio rol + `admin` en el dropdown. No ve `tecnico` y viceversa.

**Backend** — `ticket_service.py` `_ensure_assignment_access` línea 1290:
```python
if role is not None and role.crm_role_id not in actor_role_ids and not self._can_escalate_to_admin(actor, role):
    raise TicketAccessDeniedError(...)
```
`_can_escalate_to_admin` solo permite la escalada hacia `admin`. No permite asignar a `tecnico` ni a `deposito` si no son del mismo rol.

Además, línea 1293:
```python
if ticket.assigned_role_id is not None and ticket.assigned_role_id not in actor_role_ids:
    raise TicketAccessDeniedError(...)
```
Si el ticket está actualmente asignado a `tecnico` y el actor es `deposito`, esta condición bloquea la reasignación aunque el destino sea válido.

### Solución

**Paso 4 — Backend** `ticket_service.py` L222–227 — ampliar roles cruzados en `list_assignable_roles`

```python
# Antes
actor_role_ids = self._actor_role_ids(actor)
if {"tecnico", "deposito"}.intersection(actor_role_keys):
    for role in roles:
        if self._normalize_role_key(role.role_key) == "admin":
            actor_role_ids.add(role.crm_role_id)

# Después
actor_role_ids = self._actor_role_ids(actor)
if {"tecnico", "deposito"}.intersection(actor_role_keys):
    for role in roles:
        normalized = self._normalize_role_key(role.role_key)
        if normalized in {"admin", "tecnico", "deposito"}:
            actor_role_ids.add(role.crm_role_id)
```

**Paso 5 — Backend** `ticket_service.py` — agregar helper `_can_cross_assign_to_peer` (cerca de `_can_escalate_to_admin`, línea ~1300)

```python
def _can_cross_assign_to_peer(self, actor: ResolvedCrmSession, role: CrmRole | None) -> bool:
    """Deposito y tecnico pueden asignarse tickets mutuamente y a admin."""
    actor_keys = self._normalized_actor_role_keys(actor)
    if not {"tecnico", "deposito"}.intersection(actor_keys):
        return False
    normalized_target = self._normalize_role_key(getattr(role, "role_key", None)) if role else None
    return normalized_target in {"admin", "tecnico", "deposito"}
```

Modificar `_ensure_assignment_access`:

1. **Línea 1290** — reemplazar `not self._can_escalate_to_admin(actor, role)` por `not self._can_cross_assign_to_peer(actor, role)`

2. **Línea 1293** — ampliar la condición para que un tecnico/deposito pueda reasignar tickets actualmente en un rol par:

```python
# Antes
if ticket.assigned_role_id is not None and ticket.assigned_role_id not in actor_role_ids:
    raise TicketAccessDeniedError("Solo podés reasignar tickets dentro de tus propios roles.")

# Después
if ticket.assigned_role_id is not None and ticket.assigned_role_id not in actor_role_ids:
    # Tecnico y deposito pueden tomar tickets actualmente asignados al rol par
    assigned_role = next(
        (r for r in roles_cache if r.crm_role_id == ticket.assigned_role_id), None
    )
    if not self._can_cross_assign_to_peer(actor, assigned_role):
        raise TicketAccessDeniedError("Solo podés reasignar tickets dentro de tus propios roles.")
```

> `_can_escalate_to_admin` queda implícitamente cubierto por `_can_cross_assign_to_peer` (el superset). Se puede dejar como alias o eliminarlo en un refactor posterior.

---

## Bug 3 — 500 al rechazar cierre de ticket (`reject_close`)

### Error en producción

```
sqlalchemy.exc.IntegrityError: (psycopg.errors.ForeignKeyViolation)
insert or update on table "ticket_status_transitions" violates foreign key constraint
"ticket_status_transitions_ticket_comment_id_fkey"
DETAIL: Key (ticket_comment_id)=(894dd52d-...) is not present in table "ticket_comments".
```

### Diagnóstico

**Backend** — `ticket_service.py` `reject_ticket_approval` líneas 713–745:

```python
reject_comment = TicketComment(ticket_comment_id=str(uuid4()), ...)
ticket.comments.append(reject_comment)           # ← objeto nuevo, aún no en BD

# ... más cambios en ticket ...

ticket.status_history.append(
    TicketStatusTransition(
        ...
        ticket_comment_id=reject_comment.ticket_comment_id,   # ← UUID como string raw
    )
)
self._ticket_repository.save(ticket)             # commit
```

`TicketStatusTransition.ticket_comment_id` es una columna `Mapped[str | None]` con `ForeignKey("ticket_comments.ticket_comment_id")`, pero **no hay un `relationship()` de SQLAlchemy entre `TicketStatusTransition` y `TicketComment`**. Al no existir una relación ORM instrumentada, el unit-of-work no puede inferir la dependencia de INSERT entre los dos objetos nuevos. PostgreSQL puede recibir el INSERT de la transición antes que el del comentario, violando la FK.

`approve_ticket` tiene la misma causa latente (líneas 656–678), aunque se manifiesta menos porque el comentario es opcional allí.

### Solución

**Paso 6 — Backend** `ticket_service.py` línea ~720 — flush explícito en `reject_ticket_approval`

```python
# Después de:
ticket.comments.append(reject_comment)

# Agregar:
self._ticket_repository._session.flush()   # garantiza INSERT ticket_comment antes de la transición

# A continuación:
ticket.status_history.append(
    TicketStatusTransition(
        ...
        ticket_comment_id=reject_comment.ticket_comment_id,
    )
)
```

**Paso 7 — Backend** `ticket_service.py` línea ~656 — mismo parche en `approve_ticket`

```python
if ticket_comment is not None:
    ticket.comments.append(ticket_comment)
    self._ticket_repository._session.flush()   # ← agregar

ticket.status_history.append(
    TicketStatusTransition(
        ...
        ticket_comment_id=ticket_comment.ticket_comment_id if ticket_comment is not None else None,
    )
)
```

---

## Bug 4 — Tickets cerrados invisibles para roles no-admin

### Diagnóstico

Dos capas bloquean simultáneamente:

**Backend** — `ticket_service.py` `list_closed_tickets_for_actor` líneas 197–203:
```python
def list_closed_tickets_for_actor(self, actor: ResolvedCrmSession) -> list[Ticket]:
    self._ensure_admin_or_executive(actor)    # ← 403 para tecnico, deposito, etc.
    ...
```

**Frontend** — `tickets-page.component.ts` líneas 90–93:
```typescript
readonly canViewHistory = computed(() => {
  const roles = this.currentRoles();
  return roles.includes('admin') || roles.includes('ejecutivo');
});
```
Para roles no-admin, `canViewHistory()` es `false`, el frontend nunca llama a `/tickets/history/me` y vacía el signal:
```typescript
if (this.canViewHistory()) { /* carga historial */ }
this.historyTickets.set([]);
```

Cuando un ticket es cerrado, `assigned_user_id` y `assigned_role_id` se ponen a `null`, por lo que desaparece de la lista de asignados también. El ticket queda inaccesible para quien lo cerró.

### Regla de negocio requerida

- **admin / ejecutivo** → ven todos los tickets cerrados
- **Resto de roles** → ven solo los tickets cerrados en los que participaron (como asignado, asignado previo, creador, o quien cerró)

### Solución

**Paso 8 — Backend** `ticket_repository.py` — nuevo método `list_closed_tickets_for_user`

Agregar después de `list_closed_tickets` (línea 128):

```python
def list_closed_tickets_for_user(self, crm_user_id: str) -> list[Ticket]:
    from sqlalchemy import or_
    from crm_backend.models.ticket import TicketAssignmentHistory

    participated_ids = (
        select(TicketAssignmentHistory.ticket_id)
        .where(
            or_(
                TicketAssignmentHistory.assigned_user_id == crm_user_id,
                TicketAssignmentHistory.previous_user_id == crm_user_id,
            )
        )
    )
    statement = (
        select(Ticket)
        .options(*self._summary_options())
        .where(
            Ticket.status == TicketStatus.CLOSED.value,
            or_(
                Ticket.ticket_id.in_(participated_ids),
                Ticket.closed_by_crm_user_id == crm_user_id,
                Ticket.created_by_crm_user_id == crm_user_id,
            ),
        )
        .order_by(Ticket.closed_at.desc(), Ticket.updated_at.desc())
    )
    return list(self._session.scalars(statement).all())
```

**Paso 9 — Backend** `ticket_service.py` L197–203 — bifurcar por rol

```python
# Antes
def list_closed_tickets_for_actor(self, actor: ResolvedCrmSession) -> list[Ticket]:
    self._ensure_admin_or_executive(actor)
    try:
        return self._ticket_repository.list_closed_tickets()
    except Exception:
        _logger.exception(...)
        return []

# Después
def list_closed_tickets_for_actor(self, actor: ResolvedCrmSession) -> list[Ticket]:
    self._ensure_read_access(actor)
    try:
        if {"admin", "ejecutivo"}.intersection(self._normalized_actor_role_keys(actor)):
            return self._ticket_repository.list_closed_tickets()
        return self._ticket_repository.list_closed_tickets_for_user(actor.crm_user.crm_user_id)
    except Exception:
        _logger.exception("Failed to list closed tickets for actor %s", getattr(actor.crm_user, "crm_user_id", "unknown"))
        return []
```

**Paso 10 — Frontend** `tickets-page.component.ts` L90–93 — abrir `canViewHistory` a todos los roles

```typescript
// Antes
readonly canViewHistory = computed(() => {
  const roles = this.currentRoles();
  return roles.includes('admin') || roles.includes('ejecutivo');
});

// Después
readonly canViewHistory = computed(() => this.currentRoles().length > 0);
```

**Paso 11 — Frontend** `tickets-page.component.ts` L130 — ajustar contador de requests pendientes

```typescript
// Antes
let pendingRequests = this.canViewHistory() ? 4 : 3;

// Después
let pendingRequests = 4;
```

---

## Archivos a modificar

| Archivo | Cambios |
|---|---|
| `microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.ts` | L201: quitar filtro de rol en `canCreateInventoryRequest` |
| `microtv-crm-frontend/src/app/features/tickets/components/tickets-page/tickets-page.component.ts` | L90–93: abrir `canViewHistory`; L130: `pendingRequests = 4` |
| `microtv-crm-backend/src/crm_backend/services/material_flow_service.py` | L346: `increase_stock` → `decrease_stock`; L731–734: abrir `_ensure_request_create_access` |
| `microtv-crm-backend/src/crm_backend/services/ticket_service.py` | L197–203: bifurcar historial; L222–227: ampliar roles cruzados; L656: flush; L720: flush; ~L1290–1295: usar nuevo helper; ~L1300: agregar `_can_cross_assign_to_peer` |
| `microtv-crm-backend/src/crm_backend/repositories/ticket_repository.py` | Nuevo método `list_closed_tickets_for_user` después de línea 128 |

---

## Checklist de verificación

- [ ] `npm run build` sin errores de compilación
- [ ] Usuario `deposito` con ticket asignado a deposito → botón "Hacer solicitud a depósito" habilitado
- [ ] Usuario `ejecutivo` con ticket asignado a ejecutivo → mismo botón habilitado
- [ ] Crear solicitud → aprobar → despachar → `quantity_available` del producto **disminuye**
- [ ] Como `deposito`, reasignar ticket a `tecnico` → funciona
- [ ] Como `tecnico`, reasignar ticket a `deposito` → funciona
- [ ] Ambos pueden asignar a `admin`
- [ ] Ejecutivo rechaza cierre de ticket → retorna 200, ticket vuelve a `IN_PROGRESS` con comentario guardado, **sin 500**
- [ ] Ejecutivo aprueba cierre con comentario → retorna 200, **sin 500**
- [ ] `tecnico` ve tab "Historial" con sus propios tickets cerrados (los que participó)
- [ ] `deposito` ve tab "Historial" con sus propios tickets cerrados
- [ ] `admin` / `ejecutivo` ven **todos** los tickets cerrados en Historial

---

## Decisiones técnicas

- **`_can_escalate_to_admin`** queda obsoleto — reemplazado por `_can_cross_assign_to_peer` que cubre el superset (tecnico→deposito, deposito→tecnico, ambos→admin). Se puede eliminar en un refactor posterior o dejarse como alias.
- **Flush explícito vs. `relationship()`**: el flush es la corrección mínima y quirúrgica para el Bug 3. Agregar un `relationship()` SQLAlchemy entre `TicketStatusTransition` y `TicketComment` sería más robusto (el ORM inferiría el orden automáticamente) pero implica un refactor de modelo que puede diferirse.
- **`canOperateTicket()`** no se modifica — ya cubre correctamente el caso deposito cuando el ticket está asignado a ese rol.
- **Historial de tickets**: la query usa `TicketAssignmentHistory` como fuente de verdad de participación, lo que garantiza que los tickets donde el usuario fue asignado en algún momento (aunque luego se reasignara) queden visibles.
