# 0016 — Fix Push Notifications + 500s en Subtask Assignment

## Contexto

Este documento describe todos los bugs confirmados en el pipeline de notificaciones (in-app + Web Push VAPID), más el 500 recurrente en `PATCH /tasks/subtasks/{id}/assignment`. Fue producido por auditoría manual completa del código fuente y los logs de producción.

El agente que implemente este documento **no debe hacer ninguna suposición**: toda la información necesaria para ejecutar cada cambio está aquí.

---

## Estado confirmado en producción

| Hecho | Detalle |
|---|---|
| `push_subscriptions` tiene filas | Las suscripciones se registran correctamente |
| `crm_notifications` tiene sólo 2 filas | Ambas `is_read=true`, de fecha `2026-05-07`, tipo `ticket_assigned` |
| `ticket_assignment_history` tiene 12 filas | Varias de mayo 8, 11, 12 — **sin notificaciones correspondientes** |
| `PATCH /tickets/{id}/assignment` → 200 | Funciona, pero ya no crea notificaciones después del 07/05 |
| `PATCH /tasks/subtasks/3f25a419…/assignment` → 500 | Consistente, 4 intentos fallidos |
| `PATCH /tasks/subtasks/f946119f…/assignment` → 500 | Consistente, 2 intentos fallidos |
| VAPID keys | Correctas en backend y frontend `.env` de producción |
| pywebpush | Instalado en `.venv` correcto: `/opt/ycc/microtv-crm-ycc/microtv-crm-backend/.venv` |

Los logs de backend (`~/logs/crm-backend/backend.log`) son **sólo el access log de uvicorn**. Los errores Python van al **systemd journal**. El stack trace del 500 está allí, no en ese archivo.

---

## Bugs confirmados

### Bug A — `notify_bulk()` nunca despacha push (CRÍTICO)

**Archivo:** `microtv-crm-backend/src/crm_backend/services/notification_service.py`

**Severidad:** Crítica. TODOS los eventos de negocio que usan `notify_bulk()` nunca llegan como push nativo. Esto incluye: `ticket_assigned` (cuando va a múltiples receptores), alertas de stock, material flow, satisfaction forms, y cualquier otro evento que use `notify_bulk()`.

**Causa raíz:** El método `notify_bulk()` guarda las notificaciones in-app pero **no tiene ningún loop que llame a `send_to_user()`**. El método `notify()` (singular) SÍ despacha push después de guardar. Pero los eventos masivos usan `notify_bulk()`.

**Código actual (líneas 95–127 del archivo):**
```python
def notify_bulk(
    self,
    *,
    recipient_crm_user_ids: list[str],
    notification_type: NotificationType,
    title: str,
    body: str,
    entity_type: NotificationEntityType | None = None,
    entity_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    if not recipient_crm_user_ids:
        return
    notifications = [
        Notification(
            recipient_crm_user_id=user_id,
            notification_type=notification_type.value,
            title=title,
            body=body,
            entity_type=entity_type.value if entity_type is not None else None,
            entity_id=entity_id,
            metadata_json=metadata,
        )
        for user_id in recipient_crm_user_ids
    ]
    self._notification_repository.save_bulk(notifications)
    # ← AQUÍ FALTA EL DISPATCH DE PUSH
```

**Fix exacto — agregar estas líneas después de `save_bulk(notifications)`:**
```python
    self._notification_repository.save_bulk(notifications)

    if self._push_notification_service is not None:
        for user_id in recipient_crm_user_ids:
            try:
                self._push_notification_service.send_to_user(
                    crm_user_id=user_id,
                    title=title,
                    body=body,
                )
            except Exception as exc:
                logger.warning("Push bulk dispatch failed for user %s: %s", user_id, exc)
```

---

### Bug B — `send_to_user()` deja `list_for_user()` fuera del bloque seguro

**Archivo:** `microtv-crm-backend/src/crm_backend/services/push_notification_service.py`

**Severidad:** Media. Si la consulta `list_for_user()` falla por cualquier razón (timeout de DB, sesión en estado incorrecto), la excepción escapa hacia `notify()` o `notify_bulk()`. Aunque ambos tienen `except Exception`, esto puede provocar que la sesión SQLAlchemy quede en estado `PendingRollbackError` si la falla ocurre dentro de una transacción activa.

**Código actual — la línea problemática (línea 34 aproximadamente):**
```python
    def send_to_user(self, crm_user_id: str, title: str, body: str, url: str | None = None) -> None:
        if not self._settings.vapid_private_key:
            return

        subscriptions = self._repo.list_for_user(crm_user_id)   # ← FUERA de cualquier try/except
        payload = json.dumps(...)
```

**Fix exacto — envolver la consulta inicial:**
```python
    def send_to_user(self, crm_user_id: str, title: str, body: str, url: str | None = None) -> None:
        if not self._settings.vapid_private_key:
            return

        try:
            subscriptions = self._repo.list_for_user(crm_user_id)
        except Exception as exc:
            logger.warning(
                "Push dispatch skipped for user %s: failed to load subscriptions: %s",
                crm_user_id,
                exc,
            )
            return

        payload = json.dumps(
            # ... (el resto del método no cambia)
```

**Importante:** No mover el resto del método dentro del `try`. Sólo proteger esta consulta inicial con su propio `try/except` que retorna en lugar de propagar.

---

### Bug C — `expire_on_commit=True` (default) corrompe objetos cargados entre commits

**Archivo:** `microtv-crm-backend/src/crm_backend/db/session.py`

**Severidad:** Alta. Esta es la causa más probable del 500 consistente en subtask assignment.

**Mecanismo exacto:**

1. `task_repository.save(subtask.task)` → `session.commit()` → devuelve `saved_task` (recién cargado con `get_task_detail()`, todos los selectinloads aplicados)
2. `notification_repository.save(notification)` → **`session.commit()` expira TODOS los objetos en la sesión**, incluyendo `saved_task` y sus relaciones ya cargadas
3. Si `send_to_user()` corre con éxito pero `delete_by_endpoint()` falla → **segundo commit parcial** → `session` puede quedar en `PendingRollbackError`
4. El endpoint hace `TaskDetailResponse.model_validate(saved_task)` → Pydantic accede a atributos de `saved_task` → SQLAlchemy intenta lazy-load → si la sesión está en error → `InternalError` / 500

El comportamiento por defecto de SQLAlchemy (`expire_on_commit=True`) expira todos los objetos del identity map en cada `session.commit()`. En una sesión de request donde múltiples servicios hacen commits secuenciales (task_repository, notification_repository, push_subscription_repository para el delete de stale endpoints), esto provoca que el objeto ya cargado y devuelto por `task_repository.save()` sea inválido para cuando el endpoint lo pasa a Pydantic.

**Código actual (`session.py` línea 16):**
```python
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
```

**Fix exacto:**
```python
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session, expire_on_commit=False)
```

**Por qué es seguro:** Las sesiones son scoped por request en FastAPI. No hay acceso concurrente a la misma sesión. No necesitamos que los objetos se invaliden después de cada commit — si el estado más actualizado es necesario, el código ya hace `get_task_detail()` explícitamente después de cada `save()`.

**Riesgo del cambio:** Bajo. Solo afecta el comportamiento de expiry post-commit. Todos los queries explícitos siguen funcionando igual.

---

### Bug D (diagnóstico pendiente) — Stack trace del 500 en subtask assignment

**Archivo:** No determinado aún — requiere el stack trace del systemd journal.

El Bug C es la causa más probable, pero se debe confirmar con el stack trace real antes de cerrar el issue.

**Comando para obtener el stack trace:**
```bash
sudo journalctl -u crm-backend --since "2026-05-08" --no-pager \
  | grep -v 'HTTP/1\.' \
  | grep -v '^$' \
  | tail -150
```

Si el nombre del servicio no es `crm-backend`:
```bash
sudo systemctl list-units | grep -i 'crm\|ycc\|backend'
```

**Interpretar el resultado:**
- Si el error es `sqlalchemy.exc.PendingRollbackError` o `InternalError: current transaction is aborted` → el Bug C lo resuelve.
- Si el error es `pydantic.ValidationError` → hay un campo `required` en `TaskDetailResponse` que no está siendo cargado por `_detail_options()`.
- Si el error es `sqlalchemy.orm.exc.DetachedInstanceError` → los objetos están siendo expulsados de la sesión incorrectamente; el Bug C también lo resuelve.
- Si el error es algo completamente diferente (e.g., `AttributeError`, `KeyError`) → reportar aquí y no aplicar guesses.

---

## Orden de implementación recomendado

| Paso | Acción | Riesgo | Bloquea |
|------|--------|--------|---------|
| 1 | Obtener stack trace (Bug D) | Nulo (sólo lectura) | Confirma si Bug C es la causa correcta |
| 2 | Aplicar Bug C (`expire_on_commit=False`) | Bajo | Desbloquea los 500s |
| 3 | Aplicar Bug A (loop en `notify_bulk`) | Bajo | Activa push para todos los eventos masivos |
| 4 | Aplicar Bug B (wrap `list_for_user`) | Bajo | Hardens el pipeline de push |
| 5 | Reiniciar el servicio y verificar | Nulo | — |
| 6 | Verificar en DB que se crean notificaciones nuevas | Nulo | — |

---

## Archivos a modificar

### 1. `microtv-crm-backend/src/crm_backend/db/session.py`

**Cambio único — línea 16:**

Antes:
```python
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
```

Después:
```python
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session, expire_on_commit=False)
```

---

### 2. `microtv-crm-backend/src/crm_backend/services/notification_service.py`

**Cambio único — agregar loop de push en `notify_bulk()`:**

Localizar la última línea del método `notify_bulk()`:
```python
        self._notification_repository.save_bulk(notifications)
```

Reemplazar por:
```python
        self._notification_repository.save_bulk(notifications)

        if self._push_notification_service is not None:
            for user_id in recipient_crm_user_ids:
                try:
                    self._push_notification_service.send_to_user(
                        crm_user_id=user_id,
                        title=title,
                        body=body,
                    )
                except Exception as exc:
                    logger.warning("Push bulk dispatch failed for user %s: %s", user_id, exc)
```

No hay más cambios en este archivo.

---

### 3. `microtv-crm-backend/src/crm_backend/services/push_notification_service.py`

**Cambio único — wrap `list_for_user()` en try/except propio:**

Localizar el bloque que sigue al `if not self._settings.vapid_private_key: return`:

```python
        subscriptions = self._repo.list_for_user(crm_user_id)
        payload = json.dumps(
```

Reemplazar por:

```python
        try:
            subscriptions = self._repo.list_for_user(crm_user_id)
        except Exception as exc:
            logger.warning(
                "Push dispatch skipped for user %s: failed to load subscriptions: %s",
                crm_user_id,
                exc,
            )
            return

        payload = json.dumps(
```

No hay más cambios en este archivo.

---

## Verificación post-deploy

### Paso 1 — Reiniciar el servicio
```bash
sudo systemctl restart crm-backend
# o el nombre que corresponda
```

### Paso 2 — Verificar que no hay 500s en nueva asignación de subtarea

En los logs del access log:
```bash
tail -f ~/logs/crm-backend/backend.log
```

Hacer una asignación de subtarea desde el frontend y confirmar que responde 200.

### Paso 3 — Verificar que se crean notificaciones

```sql
SELECT notification_id, recipient_crm_user_id, notification_type, created_at
FROM crm_notifications
ORDER BY created_at DESC
LIMIT 10;
```

Debe aparecer una nueva fila con la asignación recién hecha.

### Paso 4 — Verificar que el push llega

En el systemd journal (en tiempo real):
```bash
sudo journalctl -u crm-backend -f | grep -v 'HTTP/1\.'
```

Debe aparecer un log como:
```
INFO - Push sent to user <uuid> endpoint https://fcm.googleapis.com/...
```
o en caso de error controlado:
```
WARNING - Push send failed for user ...
```
En ningún caso debe aparecer un traceback sin capturar.

---

## Notas de arquitectura para contexto

- La sesión SQLAlchemy es compartida por todos los repositorios dentro de un mismo request FastAPI (`use_cache=True` por defecto en `Depends`). Esto significa que `task_repository`, `notification_repository` y `push_subscription_repository` usan la **misma instancia de sesión** por request.
- `get_db_session()` en `dependencies.py` es un generator yield que cierra la sesión en el `finally`, garantizando cleanup.
- El DI chain relevante para subtask assignment:
  - `get_task_application_service()` → recibe `notification_service=notification_service`
  - `get_notification_service()` → recibe `push_notification_service=push_notification_service`
  - `get_push_notification_service()` → recibe `push_subscription_repository` (misma sesión)
- `notify()` (singular) SÍ despacha push — lo usa `ticket_service.assign_ticket()` y `task_application_service.assign_subtask()`.
- `notify_bulk()` es usado por todos los demás eventos (stock alerts, material flow, etc.).
- No hay bugs en `push_subscription_repository.py` — `delete_by_endpoint()` ya usa `commit()` correctamente.
- No hay bugs en el frontend — el polling de 30s funciona, el `startPolling()` está en `ngOnInit`, el `GET /notifications` responde 200.

---

## Archivos relevantes (rutas absolutas desde la raíz del repo)

| Archivo | Relevancia |
|---|---|
| `microtv-crm-backend/src/crm_backend/db/session.py` | Fix Bug C |
| `microtv-crm-backend/src/crm_backend/services/notification_service.py` | Fix Bug A |
| `microtv-crm-backend/src/crm_backend/services/push_notification_service.py` | Fix Bug B |
| `microtv-crm-backend/src/crm_backend/repositories/notification_repository.py` | No cambiar |
| `microtv-crm-backend/src/crm_backend/repositories/push_subscription_repository.py` | No cambiar |
| `microtv-crm-backend/src/crm_backend/services/tasks/application.py` | No cambiar (a menos que el stack trace indique otra cosa) |
| `microtv-crm-backend/src/crm_backend/services/ticket_service.py` | No cambiar |
