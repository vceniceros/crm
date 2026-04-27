# Reporte de Security Fuzzing v2 — MicroTV Identity

## Test Environment

- **Servicio:** `http://localhost:8001`
- **Base de datos:** `auth_microtv` (PostgreSQL `microtv`)
- **Referencia comparativa:** `docs/tests/2026-identity-security-fuzz.md`
- **Fecha:** 2026-03-06

---

## Tests Executed

Se re-ejecutó la suite anterior completa, con foco explícito en replay de `login_ticket`:

1. Healthcheck (`GET /health`)
2. Credential fuzzing
3. User enumeration
4. Login ticket abuse (replay, firma inválida, expirado, cruce de contexto)
5. JWT tampering
6. Token replay (sobre flujo ticket/context)
7. Tenant boundary break
8. Role escalation
9. Large payloads
10. Malformed JSON / tipos / campos faltantes
11. Token expiration handling
12. Authorization enforcement

---

## Resultados clave

### Replay de login_ticket (objetivo principal)

Secuencia solicitada:
1. login multi-tenant → `HTTP 200`
2. capturar `login_ticket`
3. primer `POST /v1/auth/select-context` → `HTTP 200`
4. segundo `POST /v1/auth/select-context` con el **mismo ticket** → `HTTP 401`

✅ **Resultado esperado cumplido**: el replay de ticket fue corregido.

### Otros resultados

- Credential fuzzing: todas las variantes devolvieron `401` sin crash.
- Enumeration básica: respuestas idénticas (`401`, `Invalid credentials.`).
- Ticket modificado (firma inválida): `401`.
- Ticket expirado: `401`.
- Tenant boundary (con ticket fresco + membership de otro usuario): `403`.
- JWT tampering (según endpoints disponibles): rechazado (`401`).
- Payload grande: ahora responde `413 Payload too large` (mejora defensiva).
- Malformed JSON / tipos inválidos / faltantes: `422`.

---

## Findings

### 1) Replay de login_ticket corregido
- **Estado:** ✅ FIXED
- **Severidad previa:** medium
- **Evidencia v2:** segundo uso del mismo ticket devuelve `401`.

### 2) Límite de payload agregado
- **Estado:** ✅ IMPROVED
- **Severidad previa:** low
- **Evidencia v2:** payload extremo en login devuelve `413` (`Payload too large`).

### 3) Códigos de validación siguen en 422
- **Estado:** ⚠️ PENDIENTE (si el contrato exige 400)
- **Severidad:** low
- **Detalle:** malformed JSON/validaciones estructurales continúan en `422` (comportamiento típico de FastAPI).

---

## Vulnerabilidades

### Corregidas desde el reporte anterior

1. **Login ticket reutilizable (replay)**
   - **Antes:** vulnerable (múltiples `200` con mismo ticket)
   - **Ahora:** corregido (`200` primer uso, `401` segundo uso)

2. **Ausencia de rechazo explícito de payload excesivo**
   - **Antes:** respondía `401` aun con payload enorme
   - **Ahora:** `413 Payload too large`

### Vigentes / no evidenciadas

- No se evidenció SQLi, bypass auth ni ruptura de aislamiento tenant.
- No se observaron fallos de firma/expiración en tokens alterados.
- La diferencia `400` vs `422` sigue como tema de contrato/API, no como bypass de seguridad.

---

## Recommended Fixes (mínimos)

1. **Mantener invalidación one-time de login_ticket** y cubrir con tests automáticos de regresión.
2. **Mantener límites de payload** en app + reverse proxy/API gateway.
3. **Definir política de errores 400 vs 422** y estandarizar contrato si aplica a clientes.
4. (Opcional) Exponer un endpoint bearer-protected de verificación para fuzzing JWT más directo.

---

## Comparison vs previous report

| Ítem | v1 | v2 | Estado |
|---|---|---|---|
| Replay de `login_ticket` | Vulnerable (`200` + `200`) | Corregido (`200` + `401`) | ✅ Fixed |
| Payload muy grande en login | Sin rechazo específico (`401`) | Rechazo explícito (`413`) | ✅ Improved |
| Enumeration básica | Mitigada (respuesta uniforme) | Igual | ✅ OK |
| Tenant isolation | Correcto (`403`) | Correcto (`403`) | ✅ OK |
| Malformed JSON status | `422` | `422` | ⚠️ Pendiente de contrato |

**Conclusión:** la corrección principal solicitada (replay de `login_ticket`) quedó validada exitosamente. Además, se observa hardening adicional en manejo de payloads grandes.
