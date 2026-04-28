# DEPLOY.md — Producción CRM YCC con Auth Interno

## 1) Objetivo y alcance
Este deploy levanta una instancia **independiente** de autenticación para CRM YCC.

- No reemplaza ni modifica auth operativo de MicroTV/Starlink.
- Puede convivir en el mismo servidor con otros auth, en puertos/procesos distintos.
- Mantiene separación de dominios:
  - Auth interno CRM: identidad, login, usuarios, roles base, JWT.
  - Backend CRM: permisos funcionales CRM, tickets, tareas, stock, clientes.

## 2) Layout recomendado

```text
/opt/ycc/crm/
  microtv-crm-ycc/
    auth.microtv.ar/
      backend/
    microtv-crm-backend/
    microtv-crm-frontend/
    lab/
  logs/
    crm-backend/
    crm-frontend/
    crm-auth/
    nginx/
```

Usuario sugerido para runtime: `ycc` (sin sudo, home en `/opt/ycc`).

## 3) Puertos internos recomendados

- CRM Backend FastAPI: `127.0.0.1:8202`
- Auth interno CRM FastAPI: `127.0.0.1:8203`
- Frontend SSR (Angular Node): `127.0.0.1:8201`
- PostgreSQL CRM: `127.0.0.1:5433`
- PostgreSQL Auth CRM: `127.0.0.1:5434`

Nota: si ya existe otra instancia de auth en 8203, usar otro puerto interno para esta instancia (por ejemplo 8303) y ajustar variables.

## 4) Pre-requisitos

```bash
sudo apt update
sudo apt install -y git python3.12 python3.12-venv python3-pip nodejs npm nginx postgresql postgresql-contrib gettext-base
```

## 5) Clonado y estructura

```bash
# como root o usuario con sudo
sudo mkdir -p /opt/ycc

# crea usuario de sistema sin privilegios sudo y con home /opt/ycc
if ! id -u ycc >/dev/null 2>&1; then
  sudo useradd --home-dir /opt/ycc --shell /bin/bash --create-home ycc
fi
sudo usermod --home /opt/ycc ycc
sudo gpasswd -d ycc sudo 2>/dev/null || true

sudo mkdir -p /opt/ycc/crm /opt/ycc/logs/{crm-backend,crm-frontend,crm-auth,nginx}
sudo chown -R ycc:ycc /opt/ycc
sudo chmod 750 /opt/ycc

sudo -iu ycc
cd /opt/ycc/crm
git clone <URL_REPO_CRM> microtv-crm-ycc
cd microtv-crm-ycc
```

Desde este punto, ejecutar pasos de aplicación como `ycc`. Mantener `sudo` solo para tareas de sistema (systemd, Nginx, paquetes, usuarios).

## 6) PostgreSQL (dos bases separadas)

```sql
-- como postgres
CREATE ROLE crm_prod_user WITH LOGIN PASSWORD '<CAMBIAR_CRM_DB_PASSWORD>';
CREATE DATABASE crm_prod OWNER crm_prod_user;

CREATE ROLE crm_auth_user WITH LOGIN PASSWORD '<CAMBIAR_AUTH_DB_PASSWORD>';
CREATE DATABASE crm_auth_prod OWNER crm_auth_user;
```

## 7) Variables de entorno

Todos los puertos de ejecución se definen por `.env` y luego son consumidos por `systemd`/`nginx`:
- Auth interno: `HOST`, `PORT`
- Backend CRM: `HOST`, `PORT`
- Frontend SSR: `PORT` (Node), `CRM_API_BASE_URL`.

### 7.1 Auth interno CRM
Archivo: `/opt/ycc/crm/microtv-crm-ycc/auth.microtv.ar/backend/.env`

```env
HOST=127.0.0.1
PORT=8203

DATABASE_URL=postgresql+psycopg://crm_auth_user:<CAMBIAR_AUTH_DB_PASSWORD>@127.0.0.1:5434/crm_auth_prod
ENVIRONMENT=production

JWT_SECRET=<JWT_SECRET_LARGO_ALEATORIO>
JWT_ALGORITHM=HS256
JWT_ISSUER=auth.crm.ycc.internal
JWT_AUDIENCE=microtv-platform

ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_MINUTES=10080
LOGIN_TICKET_EXPIRE_MINUTES=10

ALLOWED_ORIGINS=https://crm.ycc.group

CRM_AUTH_TENANT_TYPE=company
CRM_AUTH_TENANT_ID=YCC
CRM_AUTH_ADMIN_EMAIL=admin@ycc.local
CRM_AUTH_ADMIN_PASSWORD=<CAMBIAR_PASSWORD_INICIAL_FUERTE>
CRM_AUTH_ADMIN_NAME=Administrador CRM
```

### 7.2 Backend CRM
Archivo: `/opt/ycc/microtv-crm-ycc/microtv-crm-backend/.env`

```env
APP_NAME=MicroTV CRM Backend
ENVIRONMENT=production
HOST=127.0.0.1
PORT=8202

DATABASE_URL=postgresql+psycopg://crm_prod_user:<CAMBIAR_CRM_DB_PASSWORD>@127.0.0.1:5433/crm_prod

CORS_ORIGINS=https://crm.ycc.group
CORS_ORIGIN_REGEX=

AUTH_BASE_URL=http://127.0.0.1:8203
AUTH_LOGIN_PATH=/v1/auth/login
AUTH_TIMEOUT_SECONDS=10
AUTH_JWT_SECRET=<MISMO_JWT_SECRET_DEL_AUTH_INTERNO>
AUTH_JWT_ALGORITHM=HS256
AUTH_JWT_ISSUER=auth.crm.ycc.internal
AUTH_JWT_AUDIENCE=microtv-platform

# Raíz física real de multimedia (fuera del repo).
CRM_MEDIA_ROOT=/opt/ycc/crm-media
# Prefijo público que devuelve/consume la API.
CRM_MEDIA_PUBLIC_URL=/media

# Límites de backend (bytes).
PRODUCT_IMAGES_MAX_BYTES=2097152
TASK_IMAGES_MAX_BYTES=8388608
TASK_VIDEOS_MAX_BYTES=134217728
SATISFACTION_IMAGES_MAX_BYTES=8388608
SATISFACTION_VIDEOS_MAX_BYTES=67108864

AUTO_PROVISION_CRM_ROLE=true
DEFAULT_ADMIN_AUTH_ROLES=admin,platform_admin,company_admin
DEFAULT_DEPOSITO_AUTH_ROLES=operador_deposito,company_operator
DEFAULT_TECH_AUTH_ROLES=tecnico_campo
```

Importante: si cambias el `PORT` del auth en su `.env`, actualizar `AUTH_BASE_URL` para apuntar al nuevo puerto.

### 7.3 Frontend CRM
Archivo: `/opt/ycc/crm/microtv-crm-ycc/microtv-crm-frontend/.env`

```env
SERVER_NAME=crm.ycc.group
CRM_API_BASE_URL=https://crm.ycc.group/api

# Debe coincidir con CRM_MEDIA_PUBLIC_URL del backend.
CRM_MEDIA_PUBLIC_URL=/media

# Compresión/redimensión de imágenes en frontend.
IMAGE_MAX_WIDTH=1280
IMAGE_MAX_HEIGHT=1280
IMAGE_QUALITY=0.75
# Objetivo preferido. Hoy el backend valida JPG/PNG/WEBP; si pones avif, el frontend hace fallback seguro a webp.
IMAGE_TARGET_FORMAT=webp

# Límite de validación para videos en frontend (sin compresión pesada).
VIDEO_MAX_SIZE_MB=50

# Mapas (MapLibre)
NEXT_PUBLIC_MAP_STYLE_URL=https://map.microtv.ar/argentina/styles/basic-preview/style.json
NEXT_PUBLIC_MAP_DEFAULT_LAT=-34.6037
NEXT_PUBLIC_MAP_DEFAULT_LON=-58.3816
NEXT_PUBLIC_MAP_DEFAULT_ZOOM=12

PORT=8201
NODE_ENV=production
```

### 7.4 Multimedia declarativo (fuente de verdad = `.env`)

El manejo de multimedia queda 100% gobernado por variables de entorno:

- Backend escribe archivos en `CRM_MEDIA_ROOT`.
- Backend publica archivos bajo `CRM_MEDIA_PUBLIC_URL`.
- Frontend comprime/redimensiona imágenes antes de upload con `IMAGE_MAX_*`, `IMAGE_QUALITY`, `IMAGE_TARGET_FORMAT`.
- Frontend valida tamaño de video con `VIDEO_MAX_SIZE_MB` (sin compresión de video pesada).

Estructura esperada en disco (ejemplo):

```text
/opt/ycc/crm-media/
  tasks/
    images/
    videos/
  products/
    images/
  satisfaction/
    images/
    videos/
```

Reglas operativas:

- No guardar multimedia dentro del repo.
- En DB/API se persiste URL pública relativa (ej: `/media/tasks/images/archivo.webp`), no paths físicos.
- Se mantiene compatibilidad temporal con rutas legacy (`/images/...`, `/videos/...`) para registros viejos.

## 8) Instalación de dependencias

```bash
cd /opt/ycc/crm/microtv-crm-ycc

cd auth.microtv.ar/backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .

cd ../../microtv-crm-backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .

cd ../microtv-crm-frontend
npm ci
npm run build
```

### 8.1 Dependencias adicionales por multimedia (estado actual)

Asumiendo que el último commit ya es el que está en producción:

- No hay nuevas dependencias de sistema (`apt`) por este cambio de multimedia.
- No hay nuevas dependencias Python fuera de las ya instaladas por `pip install -e .`.
- Sí hay dependencia frontend (`browser-image-compression`), pero ya está versionada en `package.json`.
  - `npm ci` la instala automáticamente.
  - Si solo actualizás `.env` de frontend, igual debés regenerar build (`npm run build`) para reflejar runtime config en artefactos desplegados.

## 9) Migraciones

### 9.1 Auth interno

```bash
cd /opt/ycc/crm/microtv-crm-ycc/auth.microtv.ar/backend
source .venv/bin/activate
alembic upgrade head
python -m src.cli ensure_crm_bootstrap
```

Esto aplica:
- estructura auth
- seed idempotente de roles operativos: `admin`, `ejecutivo`, `tecnico_campo`, `operador_deposito`
- admin inicial por env (idempotente)

### 9.2 CRM backend

```bash
cd /opt/ycc/microtv-crm-ycc/microtv-crm-backend
source .venv/bin/activate
# Si el proyecto usa bootstrap interno al inicio, mantener; si agregan alembic futuro, ejecutar aquí.
```

## 10) systemd (servicios separados)

### 10.1 ycc-crm-auth.service

Archivo: `/etc/systemd/system/ycc-crm-auth.service`

```ini
[Unit]
Description=YCC CRM Internal Auth
After=network.target postgresql.service

[Service]
Type=simple
User=ycc
Group=ycc
WorkingDirectory=/opt/ycc/crm/microtv-crm-ycc/auth.microtv.ar/backend
EnvironmentFile=/opt/ycc/crm/microtv-crm-ycc/auth.microtv.ar/backend/.env
Environment=PYTHONUNBUFFERED=1
ExecStart=/bin/bash -lc '/opt/ycc/crm/microtv-crm-ycc/auth.microtv.ar/backend/.venv/bin/uvicorn src.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8203}"'
Restart=always
RestartSec=3
StandardOutput=append:/opt/ycc/logs/crm-auth/auth.log
StandardError=append:/opt/ycc/logs/crm-auth/auth.err.log

[Install]
WantedBy=multi-user.target
```

### 10.2 ycc-crm-backend.service

Archivo: `/etc/systemd/system/ycc-crm-backend.service`

```ini
[Unit]
Description=YCC CRM Backend
After=network.target postgresql.service ycc-crm-auth.service
Requires=ycc-crm-auth.service

[Service]
Type=simple
User=ycc
Group=ycc
WorkingDirectory=/opt/ycc/microtv-crm-ycc/microtv-crm-backend
EnvironmentFile=/opt/ycc/microtv-crm-ycc/microtv-crm-backend/.env
Environment=PYTHONUNBUFFERED=1
ExecStart=/bin/bash -lc '/opt/ycc/microtv-crm-ycc/microtv-crm-backend/.venv/bin/uvicorn crm_backend.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8202}"'
Restart=always
RestartSec=3
StandardOutput=append:/opt/ycc/logs/crm-backend/backend.log
StandardError=append:/opt/ycc/logs/crm-backend/backend.err.log

[Install]
WantedBy=multi-user.target
```

### 10.3 ycc-crm-frontend.service

Archivo: `/etc/systemd/system/ycc-crm-frontend.service`

```ini
[Unit]
Description=YCC CRM Frontend SSR
After=network.target ycc-crm-backend.service
Requires=ycc-crm-backend.service

[Service]
Type=simple
User=ycc
Group=ycc
WorkingDirectory=/opt/ycc/microtv-crm-ycc/microtv-crm-frontend
EnvironmentFile=/opt/ycc/microtv-crm-ycc/microtv-crm-frontend/.env
Environment=NODE_ENV=production
Environment=PORT=8201
ExecStart=/usr/bin/npm run serve:ssr:microtv-crm-frontend
Restart=always
RestartSec=3
StandardOutput=append:/opt/ycc/logs/crm-frontend/frontend.log
StandardError=append:/opt/ycc/logs/crm-frontend/frontend.err.log

[Install]
WantedBy=multi-user.target
```

Si el checkout está en `/opt/ycc/crm/microtv-crm-ycc`, reemplazar ese prefijo en `WorkingDirectory` y `EnvironmentFile`.

### 10.4 Activar servicios

```bash
sudo mkdir -p /opt/ycc/logs/crm-frontend
sudo chown ycc:ycc /opt/ycc/logs/crm-frontend

sudo mkdir -p /opt/ycc/crm-media
sudo chown -R ycc:ycc /opt/ycc/crm-media

sudo systemctl daemon-reload
sudo systemctl enable ycc-crm-auth ycc-crm-backend ycc-crm-frontend
sudo systemctl restart ycc-crm-auth ycc-crm-backend ycc-crm-frontend
```

## 11) Nginx / reverse proxy (HestiaCP)

Escenario pedido:
- Proxy Nginx SSL: `192.168.11.6` (dominio `crm.ycc.group`)
- Servicios de app: `192.168.11.8`
  - Frontend SSR: `192.168.11.8:8201`
  - Backend CRM: `192.168.11.8:8202`
  - Auth interno: `192.168.11.8:8203`

En el `server { ... }` de `crm.ycc.group`, reemplazar/ajustar los `location` para que todo pase por el mismo dominio.

```nginx
location / {
  proxy_pass http://192.168.11.8:8201;
  proxy_http_version 1.1;
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
}

# Frontend usa https://crm.ycc.group/api/... y se elimina /api antes de llegar al backend.
location /api/ {
  proxy_pass http://192.168.11.8:8202/;
  proxy_http_version 1.1;
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
}

# Archivos multimedia públicos montados por FastAPI.
location /media/ {
  proxy_pass http://192.168.11.8:8202;
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
}

# Fallback legacy opcional para registros viejos que guarden /images/* o /videos/*.
location /images/ {
  proxy_pass http://192.168.11.8:8202;
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
}

location /videos/ {
  proxy_pass http://192.168.11.8:8202;
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
}

# Exposición opcional de auth interno por el mismo dominio (solo si la necesitás).
location /v1/ {
  proxy_pass http://192.168.11.8:8203;
  proxy_http_version 1.1;
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
}

location = /nginx-health {
  access_log off;
  return 200 "healthy\n";
}
```

Importante:

- Si cambiás `CRM_MEDIA_PUBLIC_URL` en backend/frontend, también tenés que ajustar este `location` en Nginx.
- Mantener `/images/` y `/videos/` como fallback legacy hasta completar limpieza de registros históricos.

Aplicar y validar en el host `192.168.11.6`:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 11.1 CORS para este esquema

Con `crm.ycc.group` sirviendo frontend + API por mismo origen, normalmente no hace falta agregar headers CORS en Nginx.

Mantener:
- Backend CRM `.env`: `CORS_ORIGINS=https://crm.ycc.group`
- Auth interno `.env`: `ALLOWED_ORIGINS=https://crm.ycc.group`

Solo si consumís `/api` o `/v1` desde otro origen, agregar bloque `OPTIONS` + `Access-Control-Allow-*` en esos `location`.

```nginx
# ejemplo opcional para /api/ si hay clientes cross-origin
location /api/ {
  if ($request_method = OPTIONS) {
    add_header Access-Control-Allow-Origin "https://app.otro-dominio.com" always;
    add_header Access-Control-Allow-Methods "GET,POST,PUT,PATCH,DELETE,OPTIONS" always;
    add_header Access-Control-Allow-Headers "Authorization,Content-Type,X-Tenant-ID,X-Membership-ID" always;
    add_header Access-Control-Allow-Credentials "true" always;
    add_header Content-Length 0;
    add_header Content-Type text/plain;
    return 204;
  }
}
```

## 12) Verificación con curl

```bash
AUTH_PORT=$(grep '^PORT=' /opt/ycc/microtv-crm-ycc/auth.microtv.ar/backend/.env | cut -d= -f2)
BACKEND_PORT=$(grep '^PORT=' /opt/ycc/microtv-crm-ycc/microtv-crm-backend/.env | cut -d= -f2)
FRONTEND_PORT=$(grep '^PORT=' /opt/ycc/crm/microtv-crm-ycc/microtv-crm-frontend/.env | cut -d= -f2)

# salud local en 192.168.11.8
curl -sS http://127.0.0.1:${AUTH_PORT}/health
curl -sS http://127.0.0.1:${BACKEND_PORT}/health
curl -I http://127.0.0.1:${FRONTEND_PORT}/

# login admin interno
curl -sS -X POST http://127.0.0.1:${BACKEND_PORT}/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@ycc.local","password":"<PASSWORD_INICIAL>"}'

# desde cualquier host que resuelva crm.ycc.group (proxy 192.168.11.6)
curl -I https://crm.ycc.group/
curl -sS https://crm.ycc.group/api/health
curl -sS -X POST https://crm.ycc.group/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@ycc.local","password":"<PASSWORD_INICIAL>"}'

# validar configuración multimedia efectiva
grep '^CRM_MEDIA_' /opt/ycc/microtv-crm-ycc/microtv-crm-backend/.env
grep -E '^(CRM_MEDIA_PUBLIC_URL|IMAGE_MAX_WIDTH|IMAGE_MAX_HEIGHT|IMAGE_QUALITY|IMAGE_TARGET_FORMAT|VIDEO_MAX_SIZE_MB)=' /opt/ycc/crm/microtv-crm-ycc/microtv-crm-frontend/.env

# validar estructura física esperada de media
MEDIA_ROOT=$(grep '^CRM_MEDIA_ROOT=' /opt/ycc/microtv-crm-ycc/microtv-crm-backend/.env | cut -d= -f2)
ls -la "${MEDIA_ROOT}"
ls -la "${MEDIA_ROOT}/tasks" "${MEDIA_ROOT}/products" "${MEDIA_ROOT}/satisfaction"
```

## 13) Operación diaria

```bash
sudo systemctl restart ycc-crm-auth ycc-crm-backend ycc-crm-frontend nginx
sudo systemctl status ycc-crm-auth ycc-crm-backend ycc-crm-frontend nginx

journalctl -u ycc-crm-auth -f
journalctl -u ycc-crm-backend -f
journalctl -u ycc-crm-frontend -f
```

## 14) Cambio de password inicial admin

Opciones:

1. Desde UI de Configuración > Gestión de usuarios (reset password).
2. API interna (admin logueado): `PUT /api/settings/auth-users/{user_id}/reset-password`.
3. SQL directo solo emergencia (siempre usar hash Argon2 desde backend/API, nunca texto plano).

## 15) Checklist final

- [ ] Auth interno CRM responde `200` en `/health`.
- [ ] Backend CRM responde `200` en `/health`.
- [ ] Login admin inicial funciona.
- [ ] Token emitido por auth interno es aceptado por CRM backend.
- [ ] Menú Configuración > Gestión de usuarios visible para admin.
- [ ] Menú Configuración > Gestión de usuarios no visible para no admin.
- [ ] Alta de usuario sin validación de email funciona.
- [ ] Asignación de roles operativos funciona.
- [ ] Login del usuario creado funciona.
- [ ] Re-ejecutar `python -m src.cli ensure_crm_bootstrap` no duplica roles/admin.
- [ ] `CRM_MEDIA_ROOT` apunta fuera del repo y existe en disco.
- [ ] Upload de imagen en ticket/tarea/producto/satisfacción devuelve URL pública con prefijo `CRM_MEDIA_PUBLIC_URL`.
- [ ] Upload de video respeta límites configurados y sigue operativo sin compresión pesada.
- [ ] Visualización de multimedia nueva funciona por `/media/...`.
- [ ] Visualización de multimedia legacy (`/images/...` y `/videos/...`) sigue funcionando.

## 16) Seguridad mínima

- Cambiar todos los secretos por valores fuertes en producción.
- Nunca reutilizar el `JWT_SECRET` del auth productivo MicroTV/Starlink.
- Restringir puertos internos a loopback (`127.0.0.1`) y exponer solo Nginx.
- Respaldar ambas bases (`crm_prod` y `crm_auth_prod`).
- Aplicar principio de mínimo privilegio a usuarios de DB y systemd.
