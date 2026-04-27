# auth.microtv.ar Login Ticket Audit

Date: March 6, 2026

Scope:

- `backend/src/models/login_ticket.py`
- `backend/src/models/__init__.py`
- `backend/migrations/versions/20260306_0003_add_login_tickets.py`
- `backend/migrations/env.py`
- `backend/src/services/auth_service.py`
- `backend/src/security/jwt.py`
- `backend/src/api/auth.py`

Objective:

Review only the recent PostgreSQL persistence and consumption flow for `login_ticket`, with focus on production readiness, horizontal deployment, atomicity, expiration handling, and HTTP mapping.

## 1. Dominio afectado

Identity. El cambio auditado afecta exclusivamente el flujo de seleccion de contexto mediante `login_ticket` dentro del servicio `auth.microtv.ar`.

## 2. Diagnóstico técnico breve

La decision de persistir `login_ticket` en PostgreSQL es correcta para despliegue horizontal. El estado deja de depender de memoria local y pasa a una fuente compartida por todas las instancias.

El diseño actual separa razonablemente JWT y persistencia:

- el JWT lleva `jti` en `backend/src/security/jwt.py`
- la base persiste `ticket_id`, `user_id`, `created_at`, `expires_at` y `consumed_at`

La proteccion principal contra replay concurrente existe y es correcta en su base: el consumo termina en un `UPDATE` condicionado por `ticket_id`, `consumed_at IS NULL` y `expires_at > ...` en `backend/src/services/auth_service.py`. Eso evita que dos requests concurrentes consuman exitosamente el mismo ticket.

Sin embargo, el flujo todavia no esta endurecido al maximo para produccion:

- hay lecturas previas al consumo real
- la expiracion se evalua con reloj del proceso Python y no con reloj de PostgreSQL
- la validacion del ticket queda repartida entre cleanup, lectura previa y update final

El resultado es funcional y apto para multiples instancias, pero todavia con superficie innecesaria de race conditions y divergencia temporal entre nodos.

## 3. Riesgos detectados clasificados

### Crítico

- No se detecto un fallo critico que permita doble consumo exitoso del mismo `login_ticket`.

### Alto

- No se detecto un riesgo alto bloqueante en esta fase. La base del enfoque es valida para multi-instancia.

### Medio

- El consumo no usa un patron atomico puro de una sola operacion DB como unica fuente de verdad. Antes del `UPDATE` final existen lecturas previas en `backend/src/api/auth.py` y `backend/src/services/auth_service.py`. Aunque el replay doble no parece viable hoy, sobra superficie TOCTOU y round-trips evitables.
- La expiracion se evalua con `datetime.now(UTC)` desde la aplicacion en `backend/src/services/auth_service.py`. En un cluster con skew de reloj entre instancias, una instancia puede considerar valido o expirado un ticket en momentos distintos que otra.
- `get_login_ticket()` no incorpora `expires_at` dentro de la propia consulta/validacion leida. La expiracion queda distribuida entre cleanup, validacion JWT y condicion posterior del `UPDATE`, en lugar de resolverse en un punto unico.

### Bajo

- La limpieza de expirados ocurre en el hot path de emision y lectura. Eso agrega writes extra y contencion innecesaria entre instancias.
- La trazabilidad es suficiente para esta fase, pero basica. Existen `created_at`, `expires_at`, `consumed_at` y `user_id`, lo cual alcanza.
- El storage del ticket es razonable para el alcance actual: se persiste `jti`, no el JWT completo ni el secreto plano del token.

## 4. Impacto en arquitectura

Bajo.

La arquitectura elegida es correcta y consistente con las restricciones del proyecto:

- PostgreSQL compartido como fuente comun de estado
- SQLAlchemy + Alembic
- sin Redis, Kafka ni infraestructura adicional
- sin rediseñar JWT
- sin ampliar alcance a sesiones, refresh o logout

Los ajustes necesarios son puntuales sobre el flujo de consumo y no requieren rediseño arquitectonico.

## 5. Impacto en tiempo

Bajo.

La correccion minima viable es localizada y deberia limitarse a pocos cambios en la capa de servicio y en el endpoint de consumo.

## 6. Recomendación mínima viable

Endurecer el consumo para que la autoridad real del ticket sea una sola operacion atomica en PostgreSQL y que la expiracion use reloj de base de datos, no reloj del proceso Python.

No hace falta:

- cambiar de stack
- agregar infraestructura
- rediseñar JWT
- abrir alcance a sesiones, refresh o logout

## 7. Cambios concretos requeridos

1. En `backend/src/services/auth_service.py`, convertir `consume_login_ticket()` en el unico punto de verdad para consumo:
   - usar un `UPDATE` atomico contra `ticket_id`
   - incluir `user_id == sub`
   - incluir `consumed_at IS NULL`
   - incluir `expires_at > func.now()`
   - setear `consumed_at = func.now()`
   - si `rowcount != 1`, devolver `ValueError("Invalid login ticket.")`

2. En `backend/src/services/auth_service.py`, cambiar `cleanup_expired_login_tickets()` para comparar contra `func.now()` del lado de PostgreSQL.

3. En `backend/src/api/auth.py`, eliminar el pre-check `auth_service.get_login_ticket(ticket_claims)` dentro de `select-context` y dejar que:
   - JWT invalido => `401`
   - tenant no autorizado => `403`
   - consumo fallido por ticket invalido/expirado/consumido => `401`

4. Mantener el alcance actual. No tocar sesiones, refresh tokens, logout ni rediseño de claims.

## 8. Prompt exacto para VSCode

```text
Ajusta solamente estos archivos:
- backend/src/services/auth_service.py
- backend/src/api/auth.py

Objetivo:
endurecer el consumo de login_ticket para produccion horizontal usando PostgreSQL como unica fuente de verdad, sin ampliar alcance a sesiones, refresh, logout, Redis ni rediseño de JWT.

Cambios requeridos:
1. En AuthService, convierte consume_login_ticket en una operacion atomica real de base de datos:
   - usar UPDATE sobre login_tickets
   - WHERE ticket_id = :jti
   - WHERE user_id = :sub
   - WHERE consumed_at IS NULL
   - WHERE expires_at > func.now()
   - values(consumed_at=func.now())
   - si rowcount != 1 => ValueError("Invalid login ticket.")
   - commit solo en exito, rollback en fallo

2. En AuthService, cambia cleanup_expired_login_tickets para usar func.now() del lado DB en vez de datetime.now(UTC).

3. En select-context, elimina el pre-check auth_service.get_login_ticket(ticket_claims).
   El flujo debe quedar:
   - validate_login_ticket(payload.login_ticket)
   - get_user_by_id + validar email del claim
   - get_membership_context
   - consume_login_ticket(ticket_claims)
   - issue_tokens

4. Mantener mapping HTTP:
   - ticket invalido/expirado/consumido => 401
   - tenant no autorizado => 403

Restricciones:
- no tocar otros archivos
- no agregar features nuevas
- no rediseñar JWT
- no meter sesiones/refresh/logout
- no refactor global
```

## Conclusión

El cambio va en la direccion correcta y ya resuelve el problema principal de despliegue horizontal al mover `login_ticket` fuera de memoria local.

No obstante, todavia no lo consideraria completamente endurecido para produccion sin un ajuste puntual: reducir el consumo a una unica operacion atomica en DB y usar reloj de PostgreSQL para expiracion. Con ese cambio, el flujo queda alineado con el alcance actual y suficientemente robusto para multiples instancias sobre la misma base.
