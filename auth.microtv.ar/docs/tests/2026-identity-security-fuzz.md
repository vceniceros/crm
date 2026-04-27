# Reporte de Security Fuzzing — MicroTV Identity

## Test Environment

- **Servicio:** `auth.microtv.ar`
- **URL local:** `http://localhost:8001`
- **Base de datos:** `auth_microtv` (PostgreSQL, usuario `microtv`)
- **Fecha:** 2026-03-06
- **Alcance:** endpoints disponibles en el servicio (`/health`, `/v1/auth/login`, `/v1/auth/select-context`)

> Nota de alcance: en este backend no hay endpoints protegidos por Bearer token expuestos (por ejemplo `/v1/users/me`), por lo tanto la validación activa de `access_token` tampered quedó limitada.

---

## Tests Executed

1. Baseline health (`GET /health`).
2. Credential fuzzing (vacíos, formato inválido, payloads largos, inyección SQL).
3. User enumeration (usuario válido+password mala vs usuario inexistente).
4. Login ticket abuse (reuso, alteración de firma/payload, expirado, contexto cruzado).
5. JWT tampering (claims alterados y firma inválida, probado sobre flujo de login ticket).
6. Token replay (reuso repetido de login_ticket).
7. Tenant boundary break (membership de otro usuario).
8. Role escalation (roles alterados en token manipulado).
9. Large payload attacks sobre login.
10. Malformed JSON / tipos inválidos / campos faltantes.
11. Token expiration handling (ticket expirado).
12. Authorization enforcement (tenant mismatch vía select-context).

---

## Findings

### 1) Reuso ilimitado de `login_ticket` (sin invalidación one-time)
- **Severidad:** **medium**
- **Descripción:** el mismo `login_ticket` pudo usarse múltiples veces para emitir tokens válidos (`HTTP 200` repetido).
- **Impacto:** si un ticket se filtra dentro de su ventana de validez, habilita múltiples emisiones de tokens para distintos contextos del mismo usuario.
- **Reproducción:**
  1. Login multi-tenant (`POST /v1/auth/login`) y capturar `login_ticket`.
  2. Llamar `POST /v1/auth/select-context` con ese ticket (ok).
  3. Repetir la llamada con el mismo ticket (vuelve a responder `200`).

### 2) Códigos de error de validación no alineados con expectativa del prompt (422 en vez de 400)
- **Severidad:** **low**
- **Descripción:** para JSON roto, tipos inválidos o campos faltantes, la API retorna `422` (FastAPI default), no `400`.
- **Impacto:** no es una vulnerabilidad directa, pero puede afectar contratos y manejo de errores en clientes si esperan `400`.
- **Reproducción:** enviar body JSON inválido a `POST /v1/auth/login`.

### 3) Sin límites explícitos observables para payload grande en login
- **Severidad:** **low**
- **Descripción:** payloads extremadamente grandes no tumbaron el servicio, pero no se observó rechazo temprano por tamaño; la respuesta fue `401` por credenciales.
- **Impacto:** posible superficie de consumo de recursos bajo abuso de tráfico con cuerpos masivos.
- **Reproducción:** enviar email/password muy grandes a `POST /v1/auth/login`.

---

## Vulnerabilities

### Confirmadas

1. **Login ticket reutilizable** durante su período de validez.
   - Técnica: replay del ticket.
   - Evidencia: múltiples `200` con el mismo ticket.

### No confirmadas (controles efectivos)

- **SQL injection en login:** no se observó bypass ni error SQL; respuestas homogéneas `401`.
- **User enumeration básica:** respuesta idéntica para usuario inexistente y contraseña incorrecta (`401` + `Invalid credentials.`).
- **Tenant isolation:** selección de membresía de otro usuario correctamente bloqueada (`403`).
- **Token manipulado con firma inválida:** rechazado (`401`, `Invalid login ticket.`).
- **Ticket expirado:** rechazado (`401`).

---

## Recommended Fixes

1. **Invalidar `login_ticket` tras primer uso exitoso** (one-time token).
   - Guardar `jti` en store temporal (Redis/DB) y marcar como consumido.
   - Rechazar reuso con `401/403`.

2. **Agregar anti-replay adicional en login ticket**
   - `jti` + TTL corto + binding opcional (fingerprint/IP/UA, según tolerancia).

3. **Definir límites de tamaño de request body**
   - Límite en proxy/API gateway y en app.
   - Rechazar con `413 Payload Too Large` cuando corresponda.

4. **(Opcional) Normalizar política de errores de validación**
   - Si el contrato exige `400`, mapear validaciones de entrada a `400` de forma consistente.

5. **Agregar endpoint protegido de verificación (si no existe en este módulo)**
   - Facilita pruebas de hardening JWT y permite validar tampering/replay de `access_token` en runtime real.

---

## Resumen ejecutivo

El servicio mostró buen comportamiento frente a inyección, enumeración básica, manipulación de firma y aislamiento entre tenants.  
La principal debilidad detectada fue el **reuso del `login_ticket`** dentro de la ventana de validez, con impacto práctico en replay de contexto/autenticación parcial. Ajustando ese punto y aplicando límites de payload, la superficie de ataque queda notablemente más sólida.
