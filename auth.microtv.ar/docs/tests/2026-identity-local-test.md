# Reporte de pruebas funcionales locales — Identity Service

**Servicio bajo prueba:** `auth.microtv.ar`  
**Entorno local:** `http://localhost:8001`  
**Fecha de ejecución:** 2026-03-06  
**Base de datos usada:** PostgreSQL `auth_microtv` (usuario `microtv`)

---

## Environment

- URL del servicio: `http://localhost:8001`
- Healthcheck probado: `GET /health`
- Base de datos: `postgresql://microtv:***@localhost/auth_microtv`
- Estado inicial: se limpiaron usuarios de prueba y se recrearon datos controlados para escenarios single-tenant y multi-tenant.

---

## Tests Performed

1. Verificación de entorno (`GET /health`).
2. Preparación de base de datos (usuarios, memberships, roles, role_assignments).
3. Login con membresía única (`POST /v1/auth/login`).
4. Escenario multi-tenant con segunda membresía.
5. Selección de contexto (`POST /v1/auth/select-context`).
6. Aislamiento entre tenants (intento de selección de membresía ajena).
7. Validación de estructura JWT (claims esperados y ausencia de lista completa de membresías).
8. Pruebas negativas de autenticación (credenciales inválidas + usuario inactivo).

---

## Results

### Resumen Pass/Fail

- **Paso 1 — Environment Check:** ✅ PASS (HTTP 200)
- **Paso 2 — Database Preparation:** ✅ PASS
- **Paso 3 — Single Membership Login:** ✅ PASS (HTTP 200, tokens emitidos, `requires_context_selection=false`)
- **Paso 4 — Multi-Tenant Scenario:** ✅ PASS (`login_ticket` presente, `memberships` devuelto, `requires_context_selection=true`)
- **Paso 5 — Context Selection:** ✅ PASS (token emitido y contexto activo en `company_second`)
- **Paso 6 — Tenant Isolation Test:** ✅ PASS (HTTP 403 al intentar membresía de otro usuario)
- **Paso 7 — JWT Validation:** ✅ PASS (claims correctos y sin lista completa de membresías)
- **Paso 8 — Negative Authentication Tests:** ⚠️ **PARCIAL**
  - Credenciales inválidas: ✅ PASS (HTTP 401)
  - Usuario inactivo: ✅ PASS en denegación (HTTP 401)
  - No filtrar estado interno de cuenta: ❌ FAIL (se expone `"User is not active."`)

---

### Evidencia de respuestas (extractos)

#### 1) Health

- Request: `GET /health`
- HTTP: `200`
- Body:

```json
{"status":"ok"}
```

#### 3) Login con membresía única

- Request: `POST /v1/auth/login`
- HTTP: `200`
- Body (extracto):

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 3600,
  "requires_context_selection": false
}
```

Claims decodificados del `access_token`:

```json
{
  "sub": "user-admin-000000000000000000000001",
  "email": "admin@test.com",
  "active_membership": {
    "membership_id": "mship-admin-00000000000000000000001",
    "tenant_type": "company",
    "tenant_id": "company_demo",
    "roles": ["company_admin"]
  },
  "iss": "auth.microtv.ar",
  "aud": "microtv-platform",
  "iat": 1772821009,
  "exp": 1772824609
}
```

#### 4) Login multi-tenant

- Request: `POST /v1/auth/login`
- HTTP: `200`
- Body (extracto):

```json
{
  "login_ticket": "...",
  "memberships": [
    {
      "membership_id": "mship-admin-00000000000000000000001",
      "tenant_id": "company_demo"
    },
    {
      "membership_id": "mship-admin-00000000000000000000002",
      "tenant_id": "company_second"
    }
  ],
  "requires_context_selection": true
}
```

#### 5) Select context

- Request: `POST /v1/auth/select-context`
- HTTP: `200`
- Resultado: token emitido con `active_membership.tenant_id = "company_second"`.

#### 6) Aislamiento

- Request: `POST /v1/auth/select-context` con `membership_id` de otro usuario.
- HTTP: `403`
- Body:

```json
{"detail":"Selected membership is not valid for the user."}
```

#### 8) Negativas

- Credenciales inválidas:
  - HTTP: `401`
  - Body: `{"detail":"Invalid credentials."}`
- Usuario inactivo:
  - HTTP: `401`
  - Body: `{"detail":"User is not active."}`

---

## Security Observations

1. **User enumeration / account-state leakage (media):**
   - El mensaje `"User is not active."` permite inferir estado de cuenta.
   - Recomendación: respuesta uniforme para fallos de login (por ejemplo `"Invalid credentials."`) y registrar motivo real solo en logs internos.

2. **JWT scope correcto (positivo):**
   - El token contiene únicamente el contexto activo (`active_membership`) y no incluye lista completa de membresías.

3. **Aislamiento de tenant correcto (positivo):**
   - Intentos de seleccionar membresía externa se bloquean con `403`.

---

## Architectural Compliance

Validación contra:
- `docs/API_SPEC.md`
- `docs/DOMAIN_MODEL.md`

### Cumplimientos observados

- Flujo multi-tenant implementado según especificación:
  - 1 membresía => emisión directa de tokens.
  - >1 membresía => `login_ticket` + selección de contexto.
- Claims JWT esperados presentes: `sub`, `email`, `active_membership`, `iss`, `aud`, `iat`, `exp`.
- Modelo de autorización por membresía/rol consistente con `memberships`, `roles`, `role_assignments`.

### Desviaciones

- **Manejo de errores de autenticación** no cumple completamente el criterio de no exponer estado interno de cuenta en respuestas públicas.

---

## Conclusión

La validación funcional principal del servicio de identidad en local es **satisfactoria**: autenticación, multi-tenant, selección de contexto, estructura JWT y aislamiento de tenant funcionan como se espera.  

El punto a corregir es de **hardening de seguridad** en mensajes de error de autenticación para evitar filtración de estado de cuenta.
