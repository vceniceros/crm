# Entorno de desarrollo

Este documento deja cerrado el flujo inicial de login para probarlo localmente en Windows con PowerShell.

## 1. Requisitos previos

- Docker Desktop levantado.
- Python 3.12 disponible en `PATH`.
- Node.js 20+ y `npm`.
- Puertos libres: `4200`, `8001`, `8010`.

## 2. Levantar auth.microtv.ar local con seed

Parate en la raíz del workspace `microtv-crm-ycc`:

```powershell
Set-Location "e:\Documentos SYNC\gitlab clones\microtv-crm-ycc"
docker compose -f microtv-crm-backend\docker-compose.auth-local.yml up --build
```

Qué hace este compose:

- levanta PostgreSQL local de auth sólo para la red interna de Docker
- construye un contenedor específico para CRM usando `microtv-crm-backend/docker/auth-local/Dockerfile`
- corre migraciones de auth
- ejecuta el seed del CRM
- expone auth en `http://localhost:8001`

## 3. Usuarios seed creados en la base local de auth

Estos usuarios quedan creados automáticamente en `auth_microtv`:

### Admin MicroTV

- Email: `admin.crm@microtv.com`
- Password: `Passw0rd!`
- Display name: `Admin MicroTV`
- Tenant: `MICROTV`
- Rol en auth: `platform_admin`
- Bootstrap de rol local CRM esperado: `admin`

### Operador YCC Brothers

- Email: `operador.crm@yccbrothers.com`
- Password: `Passw0rd!`
- Display name: `Operador YCC Brothers`
- Tenant: `YCC`
- Rol en auth: `company_operator`
- Bootstrap de rol local CRM esperado: `deposito`

### Auxiliar Depósito YCC Brothers

- Email: `deposito.aux@yccbrothers.com`
- Password: `Passw0rd!`
- Display name: `Auxiliar Depósito YCC Brothers`
- Tenant: `YCC`
- Rol en auth: `company_operator`
- Bootstrap de rol local CRM esperado: `deposito`

### Ejecutivo YCC Brothers

- Email: `ejecutivo.crm@yccbrothers.com`
- Password: `Passw0rd!`
- Display name: `Ejecutivo YCC Brothers`
- Tenant: `YCC`
- Rol en auth: `ejecutivo`
- Bootstrap de rol local CRM esperado: `ejecutivo`

### Técnico de campo YCC Brothers

- Email: `tecnico.campo@yccbrothers.com`
- Password: `Passw0rd!`
- Display name: `Técnico de campo YCC Brothers`
- Tenant: `YCC`
- Rol en auth: `company_operator`
- Vinculación CRM local: `auth-user-ycc-tech-001` con rol local `tecnico_campo`
- Rol efectivo en UI: `tecnico`

## 4. Levantar el backend del CRM

Abrí otra terminal:

```powershell
Set-Location "e:\Documentos SYNC\gitlab clones\microtv-crm-ycc\microtv-crm-backend"
Copy-Item .env.example .env -Force
python -m pip install -e .[test]
python -m uvicorn crm_backend.main:app --reload --host 0.0.0.0 --port 8010
```

Con eso el backend queda en `http://localhost:8010`.

### Variables relevantes del `.env`

El `.env.example` ya viene listo para este flujo inicial. Si querés verificarlo, los valores importantes son:

```env
DATABASE_URL=sqlite:///./microtv_crm.db
AUTH_BASE_URL=http://localhost:8001
AUTH_LOGIN_PATH=/v1/auth/login
AUTH_JWT_SECRET=change-me
AUTH_JWT_ALGORITHM=HS256
AUTH_JWT_ISSUER=auth.microtv.ar
AUTH_JWT_AUDIENCE=microtv-platform
```

## 5. Levantar el frontend Angular

Abrí otra terminal:

```powershell
Set-Location "e:\Documentos SYNC\gitlab clones\microtv-crm-ycc\microtv-crm-frontend"
npm install
npm start
```

El frontend queda en `http://localhost:4200`.

La pantalla de login llama al backend del CRM usando esta config:

- archivo: `microtv-crm-frontend/src/app/core/config/crm-api.config.ts`
- valor actual: `http://localhost:8010`

Si necesitás apuntar a otro backend, cambiá solamente ese archivo.

## 6. Orden recomendado de arranque

```powershell
# Terminal 1
Set-Location "e:\Documentos SYNC\gitlab clones\microtv-crm-ycc"
docker compose -f microtv-crm-backend\docker-compose.auth-local.yml up --build

# Terminal 2
Set-Location "e:\Documentos SYNC\gitlab clones\microtv-crm-ycc\microtv-crm-backend"
python -m pip install -e .[test]
python -m uvicorn crm_backend.main:app --reload --host 0.0.0.0 --port 8010

# Terminal 3
Set-Location "e:\Documentos SYNC\gitlab clones\microtv-crm-ycc\microtv-crm-frontend"
npm start
```

## 6.1 Arranque desde PC apagada

Si recién arrancó la computadora, seguí exactamente estos pasos.

### Paso 1. Abrir Docker Desktop

Esperá a que Docker Desktop quede completamente levantado antes de seguir.

### Paso 2. Levantar auth local

Abrí una terminal PowerShell y ejecutá:

```powershell
Set-Location "e:\Documentos SYNC\gitlab clones\microtv-crm-ycc"
docker compose -f microtv-crm-backend\docker-compose.auth-local.yml up --build -d
```

### Paso 3. Levantar backend CRM

Abrí otra terminal PowerShell y ejecutá:

```powershell
& "e:\Documentos SYNC\gitlab clones\microtv-crm-ycc\.venv\Scripts\Activate.ps1"
Set-Location "e:\Documentos SYNC\gitlab clones\microtv-crm-ycc\microtv-crm-backend"
Copy-Item .env.example .env -Force
python -m pip install -e .[test]
python -m uvicorn crm_backend.main:app --reload --host 0.0.0.0 --port 8010
```

### Paso 4. Levantar frontend Angular

Abrí una tercera terminal PowerShell y ejecutá:

```powershell
Set-Location "e:\Documentos SYNC\gitlab clones\microtv-crm-ycc\microtv-crm-frontend"
npm install
npm start
```

### Paso 5. Entrar al CRM

Abrí en el navegador:

```text
http://localhost:4200/login
```

Usá cualquiera de estas credenciales:

```text
admin.crm@microtv.com / Passw0rd!
operador.crm@yccbrothers.com / Passw0rd!
deposito.aux@yccbrothers.com / Passw0rd!
ejecutivo.crm@yccbrothers.com / Passw0rd!
tecnico.campo@yccbrothers.com / Passw0rd!
```

## 7. Prueba manual punta a punta

1. Abrí `http://localhost:4200/login`.
2. Ingresá con alguna de las cuentas seed.
3. El frontend llama a `POST /auth/login` del CRM.
4. El backend CRM delega a auth, valida el JWT, sincroniza usuario local y devuelve sesión.
5. Si todo está bien, el frontend entra a la maqueta actual y conserva la sesión en local storage.

## 7.1 Verificación manual del técnico y clientes reales

1. Ingresá con `tecnico.campo@yccbrothers.com / Passw0rd!` y verificá que el CRM resuelva el rol UI `tecnico`.
2. Cerrá sesión e ingresá con `ejecutivo.crm@yccbrothers.com / Passw0rd!` o `admin.crm@microtv.com / Passw0rd!`.
3. Abrí el módulo de clientes y verificá que el listado consulte datos reales del backend.
4. Creá un cliente nuevo desde el formulario existente.
5. Confirmá por API o recargando la vista que el cliente persiste en la base del CRM.
6. Eliminá el cliente y verificá que desaparezca del listado por baja lógica.

## 8. Checks rápidos útiles

### Healthcheck del backend CRM

```powershell
Invoke-WebRequest http://localhost:8010/health
```

### Login directo al backend CRM

```powershell
Invoke-RestMethod \
  -Method Post \
  -Uri http://localhost:8010/auth/login \
  -ContentType 'application/json' \
  -Body '{"email":"admin.crm@microtv.com","password":"Passw0rd!"}'
```

## 9. Tests y validaciones

### Backend

```powershell
Set-Location "e:\Documentos SYNC\gitlab clones\microtv-crm-ycc\microtv-crm-backend"
pytest
```

Incluye cobertura del módulo de clientes real en `microtv-crm-backend/tests/test_clients_api.py`.

### Frontend

```powershell
Set-Location "e:\Documentos SYNC\gitlab clones\microtv-crm-ycc\microtv-crm-frontend"
npm run build
```

## 10. Limpieza rápida local

Si querés reiniciar la base local del CRM y los artefactos temporales del backend:

```powershell
Set-Location "e:\Documentos SYNC\gitlab clones\microtv-crm-ycc"
Remove-Item "microtv-crm-backend\microtv_crm.db" -ErrorAction SilentlyContinue
Remove-Item "microtv-crm-backend\debug_test.db" -ErrorAction SilentlyContinue
Remove-Item "microtv-crm-backend\tests\test_microtv_crm.db" -ErrorAction SilentlyContinue
```

Si además querés resetear la base local de auth en Docker:

```powershell
Set-Location "e:\Documentos SYNC\gitlab clones\microtv-crm-ycc"
docker compose -f microtv-crm-backend\docker-compose.auth-local.yml down -v
docker compose -f microtv-crm-backend\docker-compose.auth-local.yml up --build
```