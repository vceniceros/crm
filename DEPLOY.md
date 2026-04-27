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
    crm-auth/
    nginx/
```

Usuario sugerido para runtime: `ycc` (sin sudo, home en `/opt/ycc`).

## 3) Puertos internos recomendados

- CRM Backend FastAPI: `127.0.0.1:8010`
- Auth interno CRM FastAPI: `127.0.0.1:8001`
- Frontend estático: servido por Nginx
- PostgreSQL CRM: `127.0.0.1:5433`
- PostgreSQL Auth CRM: `127.0.0.1:5434`

Nota: si ya existe otra instancia de auth en 8001, usar otro puerto interno para esta instancia (por ejemplo 8101) y ajustar variables.

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

sudo mkdir -p /opt/ycc/crm /opt/ycc/logs/{crm-backend,crm-auth,nginx}
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
- Frontend en producción: `FRONTEND_PORT` (puerto de Nginx). El frontend Angular compilado es estático y no abre puerto propio.

### 7.1 Auth interno CRM
Archivo: `/opt/ycc/crm/microtv-crm-ycc/auth.microtv.ar/backend/.env`

```env
HOST=127.0.0.1
PORT=8001

DATABASE_URL=postgresql+psycopg://crm_auth_user:<CAMBIAR_AUTH_DB_PASSWORD>@127.0.0.1:5434/crm_auth_prod
ENVIRONMENT=production

JWT_SECRET=<JWT_SECRET_LARGO_ALEATORIO>
JWT_ALGORITHM=HS256
JWT_ISSUER=auth.crm.ycc.internal
JWT_AUDIENCE=microtv-platform

ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_MINUTES=10080
LOGIN_TICKET_EXPIRE_MINUTES=10

ALLOWED_ORIGINS=https://crm.tu-dominio.com

CRM_AUTH_TENANT_TYPE=company
CRM_AUTH_TENANT_ID=YCC
CRM_AUTH_ADMIN_EMAIL=admin@ycc.local
CRM_AUTH_ADMIN_PASSWORD=<CAMBIAR_PASSWORD_INICIAL_FUERTE>
CRM_AUTH_ADMIN_NAME=Administrador CRM
```

### 7.2 Backend CRM
Archivo: `/opt/ycc/crm/microtv-crm-ycc/microtv-crm-backend/.env`

```env
APP_NAME=MicroTV CRM Backend
ENVIRONMENT=production
HOST=127.0.0.1
PORT=8010

DATABASE_URL=postgresql+psycopg://crm_prod_user:<CAMBIAR_CRM_DB_PASSWORD>@127.0.0.1:5433/crm_prod

CORS_ORIGINS=https://crm.tu-dominio.com
CORS_ORIGIN_REGEX=

AUTH_BASE_URL=http://127.0.0.1:8001
AUTH_LOGIN_PATH=/v1/auth/login
AUTH_TIMEOUT_SECONDS=10
AUTH_JWT_SECRET=<MISMO_JWT_SECRET_DEL_AUTH_INTERNO>
AUTH_JWT_ALGORITHM=HS256
AUTH_JWT_ISSUER=auth.crm.ycc.internal
AUTH_JWT_AUDIENCE=microtv-platform

AUTO_PROVISION_CRM_ROLE=true
DEFAULT_ADMIN_AUTH_ROLES=admin,platform_admin,company_admin
DEFAULT_DEPOSITO_AUTH_ROLES=operador_deposito,company_operator
DEFAULT_TECH_AUTH_ROLES=tecnico_campo
```

Importante: si cambias el `PORT` del auth en su `.env`, actualizar `AUTH_BASE_URL` para apuntar al nuevo puerto.

### 7.3 Frontend CRM
Archivo: `/opt/ycc/crm/microtv-crm-ycc/microtv-crm-frontend/.env`

```env
SERVER_NAME=crm.tu-dominio.com
FRONTEND_PORT=80
CRM_API_BASE_URL=https://crm.tu-dominio.com/api
```

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
cd /opt/ycc/crm/microtv-crm-ycc/microtv-crm-backend
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
ExecStart=/bin/bash -lc '/opt/ycc/crm/microtv-crm-ycc/auth.microtv.ar/backend/.venv/bin/uvicorn src.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8001}"'
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
WorkingDirectory=/opt/ycc/crm/microtv-crm-ycc/microtv-crm-backend
EnvironmentFile=/opt/ycc/crm/microtv-crm-ycc/microtv-crm-backend/.env
Environment=PYTHONUNBUFFERED=1
ExecStart=/bin/bash -lc '/opt/ycc/crm/microtv-crm-ycc/microtv-crm-backend/.venv/bin/uvicorn crm_backend.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8010}"'
Restart=always
RestartSec=3
StandardOutput=append:/opt/ycc/logs/crm-backend/backend.log
StandardError=append:/opt/ycc/logs/crm-backend/backend.err.log

[Install]
WantedBy=multi-user.target
```

### 10.3 Activar servicios

```bash
sudo systemctl daemon-reload
sudo systemctl enable ycc-crm-auth ycc-crm-backend
sudo systemctl restart ycc-crm-auth ycc-crm-backend
```

## 11) Nginx / reverse proxy

Archivo plantilla: `/etc/nginx/sites-available/crm-ycc.conf.template`

```nginx
server {
  listen ${FRONTEND_PORT};
  server_name ${SERVER_NAME};

    root /opt/ycc/crm/microtv-crm-ycc/microtv-crm-frontend/dist/microtv-crm-frontend/browser;
    index index.html;

    location /api/ {
    proxy_pass http://127.0.0.1:${BACKEND_PORT}/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /nginx-health {
        access_log off;
        return 200 "healthy\n";
    }
}
```

```bash
# carga puertos/host desde .env
set -a
source /opt/ycc/crm/microtv-crm-ycc/microtv-crm-backend/.env
BACKEND_PORT="$PORT"
source /opt/ycc/crm/microtv-crm-ycc/microtv-crm-frontend/.env
set +a

: "${BACKEND_PORT:=8010}"
: "${FRONTEND_PORT:=80}"
: "${SERVER_NAME:=crm.tu-dominio.com}"

sudo envsubst '${FRONTEND_PORT} ${SERVER_NAME} ${BACKEND_PORT}' \
  < /etc/nginx/sites-available/crm-ycc.conf.template \
  > /etc/nginx/sites-available/crm-ycc.conf

sudo ln -sf /etc/nginx/sites-available/crm-ycc.conf /etc/nginx/sites-enabled/crm-ycc.conf
sudo nginx -t
sudo systemctl reload nginx
```

## 12) Verificación con curl

```bash
AUTH_PORT=$(grep '^PORT=' /opt/ycc/crm/microtv-crm-ycc/auth.microtv.ar/backend/.env | cut -d= -f2)
BACKEND_PORT=$(grep '^PORT=' /opt/ycc/crm/microtv-crm-ycc/microtv-crm-backend/.env | cut -d= -f2)
FRONTEND_PORT=$(grep '^FRONTEND_PORT=' /opt/ycc/crm/microtv-crm-ycc/microtv-crm-frontend/.env | cut -d= -f2)

# auth interno
curl -sS http://127.0.0.1:${AUTH_PORT}/health

# backend CRM
curl -sS http://127.0.0.1:${BACKEND_PORT}/health

# nginx
curl -I http://127.0.0.1:${FRONTEND_PORT}/nginx-health

# login admin interno
curl -sS -X POST http://127.0.0.1:${BACKEND_PORT}/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@ycc.local","password":"<PASSWORD_INICIAL>"}'
```

## 13) Operación diaria

```bash
sudo systemctl restart ycc-crm-auth ycc-crm-backend nginx
sudo systemctl status ycc-crm-auth ycc-crm-backend nginx

journalctl -u ycc-crm-auth -f
journalctl -u ycc-crm-backend -f
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

## 16) Seguridad mínima

- Cambiar todos los secretos por valores fuertes en producción.
- Nunca reutilizar el `JWT_SECRET` del auth productivo MicroTV/Starlink.
- Restringir puertos internos a loopback (`127.0.0.1`) y exponer solo Nginx.
- Respaldar ambas bases (`crm_prod` y `crm_auth_prod`).
- Aplicar principio de mínimo privilegio a usuarios de DB y systemd.
