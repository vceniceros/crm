# lab_deploy.md — Guía del Laboratorio Local MicroTV CRM

## 1. Propósito

Este documento describe el entorno de laboratorio local que permite probar el stack completo del CRM contra una instancia interna de autenticación y una base de datos de prueba, sin depender de repositorios externos.

El laboratorio replica el flujo de producción completo:
- auth.microtv (servicio de identidad y JWT)
- CRM Backend (FastAPI, Python)
- CRM Frontend (Angular)

---

## 2. Componentes del stack

| Componente | Tecnología | Puerto | Cómo corre |
|---|---|---|---|
| PostgreSQL de auth | Docker (postgres:16-alpine) | interno | Docker Compose |
| auth.microtv | Docker (python:3.12-slim + uvicorn) | 8001 | Docker Compose |
| CRM Backend | Python 3.12 / uvicorn | 8010 | proceso local |
| CRM Frontend | Node.js / Angular CLI (ng serve) | 4200 | proceso local |

---

## 3. Dependencias necesarias

### Software requerido

| Herramienta | Versión mínima | Propósito |
|---|---|---|
| Docker Desktop | última estable | contenedores de auth y PostgreSQL |
| Python | 3.12+ | CRM backend |
| Node.js | 20+ | CRM frontend |
| npm | 10+ | dependencias Angular |
| curl | cualquiera Windows 10+ | health check en `lab_start.bat` |

> `curl` ya viene incluido en Windows 10 versión 1803 en adelante. No requiere instalación adicional.

### Repositorio requerido

Solo se requiere este repositorio (`microtv-crm-ycc`), que ya contiene la copia interna de `auth.microtv.ar` en la subcarpeta local.

### Variables de entorno

El CRM backend usa un `.env` que se genera automáticamente desde `.env.example` si no existe. Los valores por defecto del `.env.example` son suficientes para el laboratorio:

```env
DATABASE_URL=postgresql+psycopg://crmmicrotv:crmmicrotv@localhost:5433/crm_microtv
AUTH_BASE_URL=http://localhost:8001
AUTH_JWT_SECRET=change-me
AUTH_JWT_ALGORITHM=HS256
AUTH_JWT_ISSUER=auth.crm.ycc.internal
AUTH_JWT_AUDIENCE=microtv-platform
```

> `AUTH_JWT_SECRET=change-me` debe coincidir con el `JWT_SECRET` del contenedor auth interno
> (definido en `docker-compose.auth-local.yml`, valor: `change-me`).
> No cambies uno sin cambiar el otro.

El frontend no requiere `.env`. Su URL de backend está hardcodeada en:
```
microtv-crm-frontend/src/app/core/config/crm-api.config.ts
```
Valor actual: `http://localhost:8010`.

---

## 4. Estructura de archivos del laboratorio

```
microtv-crm-ycc/
├── lab_start.bat                          <- ENTRADA PRINCIPAL del laboratorio
├── lab_deploy.md                          <- este documento
├── docs/
│   └── diagrams/
│       └── schema-propuesto-v4.sql        <- bootstrap SQL del CRM PostgreSQL
├── lab/
│   ├── crm_backend.bat                    <- helper: levanta CRM backend
│   └── crm_frontend.bat                   <- helper: levanta CRM frontend
├── microtv-crm-backend/
│   ├── docker-compose.auth-local.yml      <- compose: auth + PostgreSQL auth + PostgreSQL CRM
│   └── docker/
│       └── auth-local/
│           ├── Dockerfile                 <- imagen auth de prueba
│           └── seed_crm_auth.py           <- script de seed (usuarios de prueba)
```

> Los archivos de `docker/auth-local/` y `docker-compose.auth-local.yml` ya existían.
> `lab_start.bat`, `lab/crm_backend.bat`, `lab/crm_frontend.bat` y este documento son los únicos archivos nuevos.

---

## 5. Orden de arranque

El orden es obligatorio por dependencias de JWT:

```
PostgreSQL (auth-db)
   └── auth.microtv (crm-auth-local)  <- espera healthcheck de BD

PostgreSQL (crm-backend-db)
   └── schema-propuesto-v4.sql        <- bootstrap por psql si la BD está vacía
         └── CRM Backend            <- usa DATABASE_URL PostgreSQL real
               └── CRM Frontend   <- necesita backend para login
```

El script `lab_start.bat` respeta este orden, espera el health check de auth y además espera el `healthcheck` del PostgreSQL del CRM antes de bootstrappear el schema v4.

---

## 6. Qué hace cada script

### `lab_start.bat`

Ejecutar desde la raíz de `microtv-crm-ycc`.

1. Verifica que Docker esté activo (`docker info`).
2. Ejecuta `docker compose -f microtv-crm-backend\docker-compose.auth-local.yml up --build -d`.
   - Construye la imagen de auth desde `auth.microtv.ar/backend/`.
   - Aplica migraciones Alembic (`alembic upgrade head`).
   - Ejecuta el seed de usuarios de prueba (`seed_crm_auth.py`).
   - Levanta uvicorn en el puerto 8001.
   - Deja dos volúmenes Docker: `crm-auth-db-data` y `crm-backend-db-data`.
3. Espera hasta que el contenedor `crm-backend-db` quede `healthy`.
4. Si la BD del CRM está vacía, ejecuta `docs/diagrams/schema-propuesto-v4.sql` con `psql` dentro del contenedor.
5. Abre una ventana con `docker compose logs -f auth-local` (logs de auth en tiempo real).
6. Espera hasta que `GET http://localhost:8001/health` responda exitosamente (máximo 40 intentos × 3s = ~120s).
7. Exporta `DATABASE_URL=postgresql+psycopg://crmmicrotv:crmmicrotv@localhost:5433/crm_microtv` para la ventana del backend.
8. Abre una ventana `cmd` con `lab\crm_backend.bat`.
9. Abre una ventana `cmd` con `lab\crm_frontend.bat`.
10. Muestra resumen de URLs y usuarios de prueba.

### `lab\crm_backend.bat`

Abierto automáticamente por `lab_start.bat` (no ejecutar manualmente en circunstancias normales).

1. Valida que `microtv-crm-backend/pyproject.toml` exista.
2. Activa el venv desde `.venv/Scripts/activate.bat` si existe; si no, usa Python del sistema.
3. Copia `.env.example` → `.env` solo si `.env` no existe (no sobreescribe cambios locales).
4. Ejecuta `python -m pip install -e .[test] -q`.
5. Levanta `python -m uvicorn crm_backend.main:app --reload --host 0.0.0.0 --port 8010`.

### `lab\crm_frontend.bat`

Abierto automáticamente por `lab_start.bat`.

1. Valida que `microtv-crm-frontend/package.json` exista.
2. Verifica Node.js en PATH.
3. Ejecuta `npm install`.
4. Ejecuta `npm start` (equivalente a `ng serve --host 0.0.0.0 --allowed-hosts`).

### `docker-compose.auth-local.yml` (ya existente)

Define tres servicios:
- `auth-db`: PostgreSQL 16 Alpine, datos en volumen `crm-auth-db-data`, healthcheck cada 5s.
- `crm-backend-db`: PostgreSQL 16 Alpine, datos en volumen `crm-backend-db-data`, expuesto en `localhost:5433`, healthcheck cada 5s.
- `auth-local`: imagen construida desde `docker/auth-local/Dockerfile`, depende de `auth-db` con `condition: service_healthy` y expone healthcheck propio.

Variables de entorno inyectadas al contenedor auth:
```
DATABASE_URL=postgresql+psycopg://authmicrotv:authmicrotv@auth-db:5432/auth_microtv
JWT_SECRET=change-me
JWT_ALGORITHM=HS256
JWT_ISSUER=auth.crm.ycc.internal
JWT_AUDIENCE=microtv-platform
ALLOWED_ORIGINS=http://localhost:4200,http://localhost:5173,http://localhost:8010
CRM_AUTH_ADMIN_EMAIL=admin@ycc.local
CRM_AUTH_ADMIN_PASSWORD=changeme-secure-password
CRM_AUTH_ADMIN_NAME=Administrador CRM
CRM_AUTH_TENANT_ID=YCC
CRM_LOCAL_YCC_EMAIL=operador.crm@yccbrothers.com
CRM_LOCAL_YCC_PASSWORD=Passw0rd!
CRM_LOCAL_YCC_AUX_EMAIL=deposito.aux@yccbrothers.com
CRM_LOCAL_YCC_AUX_PASSWORD=Passw0rd!
```

### `docker/auth-local/Dockerfile` (ya existente)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY auth.microtv.ar/backend/ /app/
COPY microtv-crm-backend/docker/auth-local/seed_crm_auth.py /opt/seed/
RUN pip install "psycopg[binary]" && pip install .
CMD alembic upgrade head && python -m src.cli ensure_crm_bootstrap && python /opt/seed/seed_crm_auth.py && uvicorn src.main:app --host 0.0.0.0 --port 8001
```

El `CMD` corre tres pasos en secuencia:
1. `alembic upgrade head` — aplica todas las migraciones sobre la BD `auth_microtv`.
2. `python /opt/seed/seed_crm_auth.py` — inserta/actualiza usuarios de prueba (idempotente).
3. `uvicorn src.main:app` — levanta la API de auth.

### `docker/auth-local/seed_crm_auth.py` (ya existente)

Script Python que conecta directamente via `psycopg` y garantiza (ON CONFLICT idempotente):
- Roles operativos: `admin`, `ejecutivo`, `tecnico_campo`, `operador_deposito`
- Roles legacy de compatibilidad: `platform_admin`, `company_operator`, `company_admin`
- Compañías: `MICROTV`, `YCC Brothers`
- Usuarios con memberships y role assignments (ver sección 9)

---

## 7. Verificación de servicio

### auth.microtv

```
GET http://localhost:8001/health
Esperado: {"status": "ok"}
```

También disponible la documentación interactiva (entorno dev):
```
http://localhost:8001/docs
```

### CRM Backend

```
GET http://localhost:8010/health
Esperado: {"status": "ok"}
```

Verificar login completo:
```powershell
curl -s -X POST http://localhost:8010/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"admin.crm@microtv.com","password":"Passw0rd!"}' | ConvertFrom-Json
```

Debe devolver un JSON con `access_token`, `refresh_token`, `user` y `active_membership`.

### CRM Frontend

Abrir `http://localhost:4200` en el browser. Debe mostrar la pantalla de login.

---

## 8. URLs esperadas

| Servicio | URL |
|---|---|
| auth.microtv health | http://localhost:8001/health |
| auth.microtv docs | http://localhost:8001/docs |
| auth.microtv login endpoint | http://localhost:8001/v1/auth/login |
| CRM Backend health | http://localhost:8010/health |
| CRM Backend docs | http://localhost:8010/docs |
| CRM Frontend | http://localhost:4200 |
| PostgreSQL auth (solo referencia) | localhost:5432 (solo red interna Docker, no expuesto externamente) |
| PostgreSQL CRM | localhost:5433 |

> La BD de PostgreSQL de auth **no está expuesta** fuera de Docker. Está intencionalmente en la red interna del compose. Si necesitas acceso directo para debugging, agrega temporalmente `ports: - "5432:5432"` en el servicio `auth-db` del compose.

> La BD del CRM backend ya no usa SQLite en laboratorio. `lab_start.bat` levanta PostgreSQL en Docker, espera el healthcheck y bootstrappea `docs/diagrams/schema-propuesto-v4.sql` si la base está vacía.

---

## 9. Usuarios de prueba

Creados por `seed_crm_auth.py` en la base de datos auth (`auth_microtv`):

| Email | Password | Tenant | Rol en auth | Rol en CRM |
|---|---|---|---|---|
| `admin.crm@microtv.com` | `Passw0rd!` | MICROTV | `platform_admin` | `admin_crm` (alias app: `admin`) |
| `operador.crm@yccbrothers.com` | `Passw0rd!` | YCC | `company_operator` | `encargado_deposito` (alias app: `deposito`) |
| `deposito.aux@yccbrothers.com` | `Passw0rd!` | YCC | `company_operator` | `encargado_deposito` (alias app: `deposito`) |

### Lógica de mapeo de roles (fuente: `role_resolution_service.py`)

El CRM mapea roles del JWT de auth a roles locales CRM del schema v4 así:

1. Si el JWT incluye `platform_admin` o `company_admin` → rol CRM persistido: **`admin_crm`**; alias expuesto a la app: **`admin`**
2. Si el JWT incluye `company_operator` **y** el `tenant_id == YCC` → rol CRM persistido: **`encargado_deposito`**; alias expuesto a la app: **`deposito`**
3. Si el JWT incluye `company_operator` **y** el tenant NO es YCC → rol CRM persistido: **`tecnico_campo`**; alias expuesto a la app: **`tecnico`**

> **Nota:** El `ENTORNO_DE_DEV.md` documenta erróneamente `operador.crm@yccbrothers.com` con rol `tecnico`. El comportamiento real del código (confirmado en `_map_auth_roles_to_crm_role`) es que cualquier `company_operator` en el tenant `YCC` recibe rol `deposito`, porque `deposito_demo_tenant_id=YCC` en el `.env` del backend.

> Para probar el rol `tecnico` se necesitaría un usuario `company_operator` en un tenant distinto a `YCC`. No está incluido en el seed actual por ser innecesario para el flujo del CRM YCC.

---

## 10. Datos de prueba cargados

### Compañías/tenants

| company_id | company_name | status |
|---|---|---|
| `MICROTV` | MicroTV | active |
| `YCC` | YCC Brothers | active |

### Roles (tabla `roles` en auth)

| role_name | Uso |
|---|---|
| `platform_admin` | Admin de plataforma (acceso total) |
| `company_operator` | Operador de empresa (deposito/tecnico según tenant) |

> La migración `20260306_0006_seed_roles.py` también crea `passenger_user` y `company_admin`. El seed de prueba garantiza solo los dos roles necesarios para el CRM.

### Categorías y productos de stock (CRM Backend)

Con el laboratorio actual, `lab_start.bat` bootstrappea primero el schema v4 en PostgreSQL y luego el `lifespan` del backend completa datos operativos mínimos si faltan:
- 8 categorías de stock predefinidas
- 8 productos de stock de ejemplo
- 3 roles locales CRM: `admin_crm`, `tecnico_campo`, `encargado_deposito`
- 1 depósito base: `Deposito Principal`

Esto ocurre en el `lifespan` de la app FastAPI y es idempotente.

---

## 11. Troubleshooting

### Docker no está iniciado

**Síntoma:** `ERROR: Docker no esta corriendo.`
**Solución:** Abrir Docker Desktop y esperar a que el ícono en la barra de tareas deje de mostrar animación de carga. Luego volver a ejecutar `lab_start.bat`.

---

### Puerto ocupado

**Síntoma:** `docker: Error response from daemon: Ports are not available: listen tcp 0.0.0.0:8001: bind: address already in use.`

**Solución para port 8001:**
```powershell
# Ver qué proceso usa el puerto
netstat -ano | findstr :8001
# Detener el proceso (reemplaza PID con el número encontrado)
taskkill /PID <PID> /F
```
O detener el contenedor anterior:
```bat
docker compose -f microtv-crm-backend\docker-compose.auth-local.yml down
```

**Síntoma análogo para port 4200 (Angular):**
```powershell
netstat -ano | findstr :4200
taskkill /PID <PID> /F
```

---

### auth no responde después de 120 segundos

**Síntoma:** `ERROR: auth no respondio en ~120 segundos.`

**Diagnóstico:**
```bat
docker compose -f microtv-crm-backend\docker-compose.auth-local.yml logs
```
O mirar la ventana `auth.microtv logs [8001]` que se abrió automáticamente.

**Causas frecuentes:**

1. **auth.microtv.ar no clonado en el lugar correcto**
   El contexto de build espera que `auth.microtv.ar/` exista en el directorio padre de `microtv-crm-ycc/`. Si el build falla, authlocal no arranca. Verifica la estructura:
   ```
   [dir_padre]\
       auth.microtv.ar\
       microtv-crm-ycc\
   ```

2. **Migración Alembic falla**
   Puede verse en los logs como `alembic.util.exc.CommandError`. Suele pasar si la BD tiene estado inconsistente. Solución: destruir el volumen y reconstruir (ver "Reconstruir desde cero").

3. **Error de importación en src/**
   Si auth.microtv.ar tiene código roto, uvicorn no arranca. Ver los logs del contenedor.

---

### Migraciones no aplicadas / seed no cargado

**Síntoma:** Login falla con error 500 o la tabla `users` no existe.

**Diagnóstico:**
```bat
docker compose -f microtv-crm-backend\docker-compose.auth-local.yml logs auth-local
```
Busca líneas de `alembic` o `psycopg.errors`.

**Solución:** Reconstruir desde cero (ver sección 12).

---

### Backend CRM no conecta a auth

**Síntoma:** El backend arranca pero `POST /auth/login` devuelve 502 o 503.

**Verificaciones:**
1. ¿Está corriendo auth? `curl http://localhost:8001/health`
2. ¿El `.env` tiene `AUTH_BASE_URL=http://localhost:8001`?
3. ¿El `AUTH_JWT_SECRET` del `.env` coincide con `JWT_SECRET=change-me` del compose?

Si cambiaste el secret en un lado, cámbialo en el otro:
- Backend `.env`: `AUTH_JWT_SECRET=change-me`
- Compose: `JWT_SECRET: change-me`

---

### Frontend no conecta al backend

**Síntoma:** La pantalla de login muestra error de red o CORS.

**Verificaciones:**
1. ¿Está corriendo el backend? `curl http://localhost:8010/health`
2. ¿El backend tiene `CORS_ORIGINS=http://localhost:4200,...` y, si entrás desde celular/LAN, `CORS_ORIGIN_REGEX=^https?://(localhost|127\.0\.0\.1|192\.168...)(:\d+)?$` en el `.env`?
3. ¿El frontend apunta al puerto correcto? Ver `src/app/core/config/crm-api.config.ts`, debe decir `http://localhost:8010`.

---

### npm install falla

**Síntoma:** Error durante `npm install` en la ventana del frontend.

**Soluciones:**
```bat
cd microtv-crm-frontend
rmdir /s /q node_modules
del package-lock.json
npm install
```
Si persiste, verificar versión de Node: `node --version` (requiere 20+).

---

### pip install falla en el backend

**Síntoma:** Error durante `pip install -e .[test]`.

**Verificaciones:**
1. Python 3.12+ en PATH: `python --version`
2. Si usas venv, que esté activado: `where python` debe mostrar la ruta del venv.
3. Dependencias del sistema para `psycopg[binary]` (en Windows no hay deps adicionales, viene precompilado).

---

## 12. Notas de mantenimiento

### Dónde cambiar credenciales de prueba

Las credenciales de los usuarios de prueba se definen en:
```
microtv-crm-backend\docker-compose.auth-local.yml
```
Variables:
```yaml
CRM_LOCAL_ADMIN_EMAIL: admin.crm@microtv.com
CRM_LOCAL_ADMIN_PASSWORD: Passw0rd!
CRM_LOCAL_YCC_EMAIL: operador.crm@yccbrothers.com
CRM_LOCAL_YCC_PASSWORD: Passw0rd!
CRM_LOCAL_YCC_AUX_EMAIL: deposito.aux@yccbrothers.com
CRM_LOCAL_YCC_AUX_PASSWORD: Passw0rd!
```
El seed las lee desde estas variables de entorno. Cambiarlas y volver a ejecutar `docker compose up --build` aplica los cambios (el seed es idempotente, actualiza passwords existentes con ON CONFLICT DO UPDATE).

### Dónde agregar más usuarios de prueba

Editar:
```
microtv-crm-backend\docker/auth-local\seed_crm_auth.py
```

Seguir el patrón existente con las funciones `ensure_user()` y `ensure_membership()`. Agregar las variables de entorno correspondientes en el `docker-compose.auth-local.yml` para no hardcodear credenciales.

Ejemplo para agregar un usuario `tecnico` en un tenant distinto:
```python
# En seed_crm_auth.py, dentro de main():
tecnico_id = ensure_user(cursor, email=os.getenv("CRM_LOCAL_TECNICO_EMAIL", "tecnico@otrocliente.com"), ...)
ensure_company(cursor, company_id="OTRO", company_name="Otro Cliente")
ensure_membership(cursor, user_id=tecnico_id, company_id="OTRO", role_id=company_operator_role_id)
```

### Cómo reconstruir desde cero

Si la BD está corrompida, hay conflictos de migración, o querés un estado limpio:

```bat
:: Desde la raíz de microtv-crm-ycc
docker compose -f microtv-crm-backend\docker-compose.auth-local.yml down -v
```

La flag `-v` elimina el volumen `crm-auth-db-data`. La próxima ejecución de `lab_start.bat` o `docker compose up --build` parte de cero: nueva BD, migraciones desde el principio, seed completo.

Borrar también la BD SQLite del CRM backend si querés estado limpio del CRM también:
```bat
del microtv-crm-backend\microtv_crm.db
```

### Actualizar el Dockerfile de auth después de cambios en auth.microtv.ar

El Dockerfile copia el código de `auth.microtv.ar/backend/` en build time. Al hacer cambios en ese repo y ejecutar `docker compose up --build`, la imagen se reconstruye automáticamente incluyendo los cambios.

Las migraciones Alembic nuevas se aplican automáticamente con `alembic upgrade head` al arrancar el contenedor.

### JWT_SECRET

En laboratorio usa `change-me`. Si necesitás un secret diferente, cambiar en:
1. `microtv-crm-backend\docker-compose.auth-local.yml` → `JWT_SECRET`
2. `microtv-crm-backend\.env` → `AUTH_JWT_SECRET`

Ambos deben tener el mismo valor o el CRM no podrá validar los tokens que emite auth.

---

## Apéndice: Comandos equivalentes manuales

Si preferís levantar cada componente sin el `.bat`:

### 1. auth (Docker)
```powershell
Set-Location "e:\Documentos SYNC\gitlab clones\microtv-crm-ycc"
docker compose -f microtv-crm-backend\docker-compose.auth-local.yml up --build
# Con -d para detached (logs con: docker compose ... logs -f auth-local)
```

### 2. CRM Backend
```powershell
Set-Location "e:\Documentos SYNC\gitlab clones\microtv-crm-ycc\microtv-crm-backend"
# Activar venv si existe:
& "..\\.venv\Scripts\Activate.ps1"
Copy-Item .env.example .env -Force
python -m pip install -e .[test]
python -m uvicorn crm_backend.main:app --reload --host 0.0.0.0 --port 8010
```

### 3. CRM Frontend
```powershell
Set-Location "e:\Documentos SYNC\gitlab clones\microtv-crm-ycc\microtv-crm-frontend"
npm install
npm start
```

### 4. Detener todo
```powershell
# Ctrl+C en terminales de backend y frontend
# Detener Docker:
docker compose -f microtv-crm-backend\docker-compose.auth-local.yml down
# Con -v para borrar volúmenes (rebuild desde cero):
docker compose -f microtv-crm-backend\docker-compose.auth-local.yml down -v
```
