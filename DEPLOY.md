# DEPLOY.md — Producción CRM MicroTV

**Versión:** 1.0  
**Fecha:** 2026-04-24  
**Audiencia:** Sudoers en `/opt/ycc`  
**Entorno:** Ubuntu Server / Debian compatible  

---

## 📋 Tabla de contenidos

1. [Supuestos del entorno](#supuestos-del-entorno)
2. [Estructura de directorios](#estructura-de-directorios-en-servidor)
3. [Pre-deploy: Preparación del servidor](#pre-deploy-preparación-del-servidor)
4. [PostgreSQL: Base de datos](#postgresql-base-de-datos)
5. [Backend: FastAPI](#backend-fastapi)
6. [Frontend: Angular](#frontend-angular)
7. [Nginx: Reverse proxy](#nginx-reverse-proxy)
8. [Systemd: Proceso backend](#systemd-proceso-backend)
9. [HTTPS/SSL](#httpsssl-certbot)
10. [Verificación post-deploy](#verificación-post-deploy)
11. [Backups](#backups)
12. [Actualización de versión](#actualización-de-versión)
13. [Rollback](#rollback)
14. [Troubleshooting](#troubleshooting)

---

## Supuestos del entorno

```
Usuario deploy:        sudoer (capaz de ejecutar sudo sin contraseña)
Home deploy:           /opt/ycc
Sistema operativo:     Ubuntu Server 20.04 LTS o superior / Debian 11+
Backend:               FastAPI (uvicorn ASGI)
Frontend:              Angular 21.2
Base de datos:         PostgreSQL 16
Reverse proxy:         Nginx
Proceso backend:       systemd (ycc-crm-backend)
Frontend estático:     Nginx (SPA con service worker)
Dominio producción:    crm.microtv.ar (REEMPLAZAR CON DOMINIO REAL)
Auth externo:          https://auth.microtv.ar
```

**⚠️ Si alguno de estos supuestos es incorrecto, ajustar ahora antes de continuar.**

---

## Estructura de directorios en servidor

```
/opt/ycc/
├── crm/
│   ├── backend/
│   │   ├── .env                    # Variables de entorno (NO COMMITEAR)
│   │   ├── .git/
│   │   ├── venv/                   # Python virtualenv
│   │   ├── src/crm_backend/
│   │   ├── public/                 # Imágenes y videos
│   │   │   ├── images/
│   │   │   └── videos/
│   │   ├── pyproject.toml
│   │   └── [otros archivos del repo]
│   │
│   ├── frontend/
│   │   ├── dist/                   # Build output (SSR)
│   │   ├── node_modules/
│   │   ├── src/
│   │   ├── package.json
│   │   └── [otros archivos del repo]
│   │
│   ├── logs/
│   │   ├── backend.log
│   │   ├── backend.err
│   │   └── nginx/
│   │
│   ├── backups/
│   │   ├── crm_prod_2026-04-24_123456.sql
│   │   └── [backups históricos]
│   │
│   └── .env                        # Archivo raíz (opcional, para facilitar backups)
│
└── [otros servicios de /opt/ycc si existen]
```

---

## Pre-deploy: Preparación del servidor

### 1. Crear usuario y estructura base

```bash
# Si no existe usuario 'ycc'
sudo useradd -m -d /opt/ycc -s /bin/bash ycc
# Agregar a sudoers si es necesario
# sudo visudo -> añadir: ycc ALL=(ALL) NOPASSWD: ALL

# Crear estructura base
sudo mkdir -p /opt/ycc/crm/{backend,frontend,logs,backups}
sudo chown -R ycc:ycc /opt/ycc/crm
sudo chmod 755 /opt/ycc/crm
```

### 2. Actualizar sistema e instalar dependencias base

```bash
sudo apt update
sudo apt upgrade -y

sudo apt install -y \
  git \
  curl \
  wget \
  vim \
  build-essential \
  libssl-dev \
  libffi-dev
```

### 3. Instalar PostgreSQL

```bash
# Ubuntu 20.04 LTS - PostgreSQL 16
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update
sudo apt install -y postgresql-16 postgresql-contrib-16

# Verificar que está corriendo
sudo systemctl status postgresql
```

### 4. Instalar Python 3.12+

```bash
sudo apt install -y \
  python3.12 \
  python3.12-venv \
  python3.12-dev \
  python3-pip

# Verificar versión
python3.12 --version
```

### 5. Instalar Node.js y npm

```bash
# Node.js LTS (recomendado: Node 20+)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verificar
node --version  # v20.x.x
npm --version   # 10.8.2+
```

### 6. Instalar Nginx

```bash
sudo apt install -y nginx

# Verificar e iniciar
sudo systemctl enable nginx
sudo systemctl start nginx
sudo systemctl status nginx
```

---

## PostgreSQL: Base de datos

### 1. Crear base de datos y usuario

```bash
# Conectarse a PostgreSQL como superuser
sudo -u postgres psql

# En la consola psql:
```

```sql
-- Crear base de datos
CREATE DATABASE crm_prod
  ENCODING 'UTF8'
  LC_COLLATE 'en_US.UTF-8'
  LC_CTYPE 'en_US.UTF-8';

-- Crear usuario con contraseña FUERTE (CAMBIAR)
CREATE USER crm_prod_user WITH PASSWORD 'CAMBIAR_PASSWORD_SUPER_FUERTE_2026';

-- Asignar privilegios
GRANT ALL PRIVILEGES ON DATABASE crm_prod TO crm_prod_user;
ALTER ROLE crm_prod_user SET client_encoding = 'utf8';
ALTER ROLE crm_prod_user SET default_transaction_isolation = 'read committed';
ALTER ROLE crm_prod_user SET default_transaction_deferrable = on;
ALTER ROLE crm_prod_user SET default_transaction_read_only = off;

-- Salir
\q
```

### 2. Validar conexión

```bash
# Desde el user 'ycc'
psql -U crm_prod_user -d crm_prod -h localhost \
  -c "SELECT version();"

# Debe retornar la versión de PostgreSQL sin errores
```

### 3. Restricciones de acceso (pg_hba.conf)

Editar `/etc/postgresql/16/main/pg_hba.conf`:

```bash
sudo nano /etc/postgresql/16/main/pg_hba.conf
```

Asegurarse de tener:

```
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             postgres                                peer
local   crm_prod        crm_prod_user                           md5
host    crm_prod        crm_prod_user   127.0.0.1/32            md5
host    crm_prod        crm_prod_user   ::1/128                 md5
```

Reiniciar PostgreSQL:

```bash
sudo systemctl restart postgresql
```

---

## Backend: FastAPI

### 1. Clonar repositorio

```bash
cd /opt/ycc/crm/backend

# Si no está clonado aún
git clone <URL_REPO_BACKEND> .

# O actualizar si ya existe
git fetch origin
git checkout main
git pull origin main
```

### 2. Crear virtualenv Python

```bash
cd /opt/ycc/crm/backend

python3.12 -m venv venv
source venv/bin/activate

# Actualizar pip
pip install --upgrade pip setuptools wheel
```

### 3. Instalar dependencias

```bash
cd /opt/ycc/crm/backend
source venv/bin/activate

pip install -e ".[test]"
# Esto instala según pyproject.toml:
# - fastapi>=0.115
# - uvicorn[standard]>=0.34
# - sqlalchemy>=2.0
# - psycopg[binary]>=3.2
# - pydantic-settings>=2.9
# - python-dotenv>=1.1
# - pyjwt>=2.10
# - etc.
```

### 4. Crear archivo .env producción

```bash
cd /opt/ycc/crm/backend
nano .env
```

**Contenido de `.env` (REEMPLAZAR VALORES):**

```bash
# ==============================================================================
# APLICACIÓN
# ==============================================================================
APP_NAME=MicroTV CRM Backend
ENVIRONMENT=production
HOST=127.0.0.1
PORT=8010

# ==============================================================================
# BASE DE DATOS
# ==============================================================================
# Formato: postgresql+psycopg://usuario:password@host:puerto/database
DATABASE_URL=postgresql+psycopg://crm_prod_user:CAMBIAR_PASSWORD_SUPER_FUERTE_2026@localhost:5432/crm_prod

# ==============================================================================
# CORS
# ==============================================================================
# Dominios permitidos para solicitudes desde navegadores
CORS_ORIGINS=https://crm.microtv.ar
CORS_ORIGIN_REGEX=

# ==============================================================================
# AUTENTICACIÓN EXTERNA (auth.microtv.ar)
# ==============================================================================
AUTH_BASE_URL=https://auth.microtv.ar
AUTH_LOGIN_PATH=/v1/auth/login
AUTH_TIMEOUT_SECONDS=10
AUTH_JWT_SECRET=CAMBIAR_JWT_SECRET_COMPARTIDO_CON_AUTH
AUTH_JWT_ALGORITHM=HS256
AUTH_JWT_ISSUER=auth.microtv.ar
AUTH_JWT_AUDIENCE=microtv-platform

# ==============================================================================
# ROLES Y PROVISIÓN
# ==============================================================================
AUTO_PROVISION_CRM_ROLE=true
DEFAULT_ADMIN_AUTH_ROLES=platform_admin,company_admin
DEFAULT_DEPOSITO_AUTH_ROLES=company_operator
DEFAULT_TECH_AUTH_ROLES=company_operator
DEPOSITO_DEMO_TENANT_ID=YCC

# ==============================================================================
# LÍMITES DE ARCHIVOS
# ==============================================================================
PRODUCT_IMAGES_MAX_BYTES=2097152
TASK_IMAGES_MAX_BYTES=8388608
TASK_VIDEOS_MAX_BYTES=134217728
```

**⚠️ IMPORTANTE:**
- No commitear `.env` (verificar que está en `.gitignore`)
- Guardar contraseña de DB en lugar seguro (gestor de secretos)
- Cambiar `AUTH_JWT_SECRET` según coordine con auth.microtv.ar
- CORS_ORIGINS debe ser el dominio final

### 5. Validar configuración

```bash
cd /opt/ycc/crm/backend
source venv/bin/activate

python -c "from crm_backend.core.config import get_settings; s = get_settings(); print(f'App: {s.app_name}'); print(f'Env: {s.environment}'); print(f'DB: {s.database_url[:50]}...')"

# Debe mostrar app name, environment=production, y la BD sin errores
```

### 6. Validar conexión a DB

```bash
cd /opt/ycc/crm/backend
source venv/bin/activate

python << 'EOF'
from crm_backend.db.session import SessionLocal
try:
    session = SessionLocal()
    result = session.execute("SELECT 1")
    print("✓ Conexión a DB exitosa")
    session.close()
except Exception as e:
    print(f"✗ Error de conexión: {e}")
EOF
```

---

## Frontend: Angular

### 1. Clonar repositorio

```bash
cd /opt/ycc/crm/frontend

# Si no está clonado aún
git clone <URL_REPO_FRONTEND> .

# O actualizar si ya existe
git fetch origin
git checkout main
git pull origin main
```

### 2. Instalar dependencias npm

```bash
cd /opt/ycc/crm/frontend

npm ci
# (usar 'npm ci' en producción en lugar de 'npm install' para lockfile exacto)
```

### 3. Crear archivo de configuración runtime

El frontend usa `sync-runtime-env.mjs` para inyectar variables en tiempo de compilación:

```bash
cd /opt/ycc/crm/frontend
nano .env.production
```

**Contenido de `.env.production`:**

```bash
# Este archivo se lee durante `npm run build` (pre-build hook)
# Las variables se sincronizan a src/runtime-env.json

ANGULAR_APP_API_BASE_URL=https://crm.microtv.ar/api
ANGULAR_APP_AUTH_BASE_URL=https://auth.microtv.ar
```

(Ajustar valores según tu configuración)

### 4. Build producción

```bash
cd /opt/ycc/crm/frontend

npm run build
# Pre-build hook ejecuta sync-runtime-env
# Genera ./dist/ con SSR habilitado
```

**Estructura de output:**

```
dist/
├── browser/              # Build browser (SPA)
│   ├── index.html
│   ├── *.js
│   ├── *.css
│   ├── ngsw.json        # Service worker manifest
│   └── manifest.webmanifest
├── server/               # Build servidor (SSR)
│   ├── server.mjs
│   └── ...
└── [assets]
```

### 5. Validar build

```bash
cd /opt/ycc/crm/frontend
ls -la dist/browser/index.html dist/server/server.mjs

# Ambos deben existir
```

---

## Nginx: Reverse proxy

### 1. Crear archivo de configuración

```bash
sudo nano /etc/nginx/sites-available/crm.microtv.ar
```

**Contenido (REEMPLAZAR DOMINIOS Y RUTAS):**

```nginx
# ==============================================================================
# MicroTV CRM Frontend + API Proxy
# ==============================================================================

upstream backend_upstream {
    # Backend FastAPI escuchando en localhost:8010
    server 127.0.0.1:8010 fail_timeout=0;
}

server {
    listen 80;
    listen [::]:80;
    server_name crm.microtv.ar;

    # Redirigir HTTP a HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name crm.microtv.ar;

    # ==============================================================================
    # SSL/TLS (Certbot - ver sección HTTPS)
    # ==============================================================================
    ssl_certificate /etc/letsencrypt/live/crm.microtv.ar/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/crm.microtv.ar/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # ==============================================================================
    # Logging
    # ==============================================================================
    access_log /opt/ycc/crm/logs/nginx/crm_access.log;
    error_log /opt/ycc/crm/logs/nginx/crm_error.log;

    # ==============================================================================
    # Frontend SPA (Angular)
    # ==============================================================================
    root /opt/ycc/crm/frontend/dist/browser;
    index index.html;

    # Límite de tamaño para subida de archivos
    client_max_body_size 256M;

    location / {
        # Servir archivo estático si existe
        # Si no existe, servir index.html (SPA routing)
        try_files $uri $uri/ /index.html;

        # Headers para caché de SPA
        expires -1;
        add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }

    # Service Worker (caché controlado por el navegador)
    location = /ngsw.json {
        expires -1;
        add_header Cache-Control "no-store, no-cache, must-revalidate";
    }

    # Manifest Web App
    location = /manifest.webmanifest {
        add_header Content-Type "application/manifest+json";
        expires 1d;
        add_header Cache-Control "public, max-age=86400";
    }

    # Assets estáticos (con fingerprinting de Angular)
    location ~ ^/.*\.(js|css|woff2|woff|ttf|eot|svg|png|jpg|jpeg|gif|ico)$ {
        expires 1y;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    # ==============================================================================
    # Backend API (/api/*)
    # ==============================================================================
    location /api/ {
        proxy_pass http://backend_upstream;
        proxy_http_version 1.1;

        # Headers proxy
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 24 4k;

        # No cachear respuestas de API
        add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate";
        add_header Pragma "no-cache";
    }

    # ==============================================================================
    # Archivos públicos (imágenes, videos)
    # ==============================================================================
    location /images/ {
        alias /opt/ycc/crm/backend/public/images/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
        access_log off;
    }

    location /videos/ {
        alias /opt/ycc/crm/backend/public/videos/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
        access_log off;
    }

    # ==============================================================================
    # Health checks
    # ==============================================================================
    location /nginx-health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    # ==============================================================================
    # Denegar acceso a archivos privados
    # ==============================================================================
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    location ~ ~$ {
        deny all;
        access_log off;
        log_not_found off;
    }
}
```

### 2. Habilitar sitio en Nginx

```bash
sudo ln -s /etc/nginx/sites-available/crm.microtv.ar /etc/nginx/sites-enabled/

# Crear directorio de logs si no existe
sudo mkdir -p /opt/ycc/crm/logs/nginx
sudo chown -R www-data:www-data /opt/ycc/crm/logs/nginx

# Validar sintaxis
sudo nginx -t

# Si dice "OK", recargar
sudo systemctl reload nginx
```

### 3. Validar disponibilidad Nginx

```bash
# Solo debe responderse en HTTPS después de instalar SSL
curl -I http://crm.microtv.ar
# Debe redirigir a https:// (301)

# Verificar que NO responde el backend directamente
curl -I http://127.0.0.1:8010
# No debería ser accesible (firewall o solo localhost)
```

---

## Systemd: Proceso backend

### 1. Crear archivo de servicio

```bash
sudo nano /etc/systemd/system/ycc-crm-backend.service
```

**Contenido:**

```ini
[Unit]
Description=YCC CRM Backend (FastAPI)
Documentation=https://docs.fastapi.tiangolo.com/
After=network.target postgresql.service

[Service]
Type=notify
User=ycc
Group=ycc
WorkingDirectory=/opt/ycc/crm/backend

# Cargar variables de entorno desde .env
EnvironmentFile=/opt/ycc/crm/backend/.env

# Comando para ejecutar
ExecStart=/opt/ycc/crm/backend/venv/bin/uvicorn \
    crm_backend.main:app \
    --host 127.0.0.1 \
    --port 8010 \
    --workers 4 \
    --access-log \
    --log-level info

# Reinicio automático
Restart=always
RestartSec=10

# Límites de recursos
MemoryLimit=1G
CPUQuota=80%

# Logs
StandardOutput=append:/opt/ycc/crm/logs/backend.log
StandardError=append:/opt/ycc/crm/logs/backend.err

[Install]
WantedBy=multi-user.target
```

### 2. Registrar y habilitar servicio

```bash
sudo systemctl daemon-reload
sudo systemctl enable ycc-crm-backend
sudo systemctl start ycc-crm-backend

# Verificar estado
sudo systemctl status ycc-crm-backend

# Ver logs en vivo
sudo journalctl -u ycc-crm-backend -f
```

### 3. Comandos útiles de systemd

```bash
# Ver estado
sudo systemctl status ycc-crm-backend

# Ver últimas líneas de logs
sudo journalctl -u ycc-crm-backend -n 50

# Ver logs en vivo (sigue)
sudo journalctl -u ycc-crm-backend -f

# Reiniciar servicio
sudo systemctl restart ycc-crm-backend

# Detener servicio
sudo systemctl stop ycc-crm-backend

# Ver si hay errores
sudo systemctl status ycc-crm-backend --no-pager

# Validar que escucha en puerto correcto
sudo ss -tlnp | grep 8010
```

---

## HTTPS/SSL (Certbot)

### 1. Instalar Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 2. Obtener certificado

```bash
sudo certbot --nginx -d crm.microtv.ar
# Seguir el wizard interactivo
# Ingresar email para notificaciones de renovación
# Aceptar términos
```

### 3. Verificar renovación automática

```bash
sudo systemctl status certbot.timer

# Probar renovación en dry-run
sudo certbot renew --dry-run
```

### 4. Configuración en Nginx (ya incluida arriba)

El archivo `crm.microtv.ar` ya tiene rutas apuntando a Certbot:

```nginx
ssl_certificate /etc/letsencrypt/live/crm.microtv.ar/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/crm.microtv.ar/privkey.pem;
```

---

## Verificación post-deploy

### Checklist 1: Servicios base

```bash
# PostgreSQL corriendo
sudo systemctl status postgresql
sudo pg_isready -U crm_prod_user -d crm_prod

# Backend corriendo
sudo systemctl status ycc-crm-backend

# Nginx corriendo
sudo systemctl status nginx
sudo nginx -t
```

### Checklist 2: Conectividad

```bash
# Backend responde en localhost
curl -I http://127.0.0.1:8010/health

# Frontend accesible vía Nginx HTTPS
curl -I https://crm.microtv.ar
# Debe devolver 200 OK (no 502, 503, etc.)

# API accesible vía Nginx
curl -I https://crm.microtv.ar/api/health

# Verificar Service Worker
curl -I https://crm.microtv.ar/ngsw.json

# Verificar Manifest
curl -I https://crm.microtv.ar/manifest.webmanifest
```

### Checklist 3: Logs

```bash
# Backend
sudo journalctl -u ycc-crm-backend --no-pager -n 100 | tail -20

# Nginx
sudo tail -20 /opt/ycc/crm/logs/nginx/crm_error.log
sudo tail -20 /opt/ycc/crm/logs/nginx/crm_access.log

# PostgreSQL
sudo tail -20 /var/log/postgresql/postgresql-16-main.log
```

### Checklist 4: Funcionalidad manual

Desde navegador, abrir `https://crm.microtv.ar`:

- [ ] Página carga sin errores 404/502/503
- [ ] PWA es instalable (ícono + "Instalar")
- [ ] Service Worker registrado (DevTools → Application → Service Workers)
- [ ] Intenta login
- [ ] Intenta acceder a dashboard (verifica que llama a `/api/...`)
- [ ] Verifica que las imágenes/videos cargan desde `/images/` y `/videos/`
- [ ] Intenta subir archivo (si aplica)
- [ ] Intenta cambiar de rol (si aplica)
- [ ] Intenta logout

### Checklist 5: Seguridad

```bash
# Certificado HTTPS válido
curl -I https://crm.microtv.ar | grep "HTTP\|Strict"

# Verificar que HTTP redirige a HTTPS
curl -I http://crm.microtv.ar | grep "301\|Location"

# Verificar que backend NO es accesible directamente
# (firewalled o solo localhost)
telnet crm.microtv.ar 8010
# Debe fallar (connection refused)
```

---

## Backups

### PostgreSQL: Backup completo

```bash
# Backup de BD (como user ycc)
cd /opt/ycc/crm/backups

pg_dump -U crm_prod_user \
  -d crm_prod \
  -F c \
  -f "crm_prod_$(date +%Y-%m-%d_%H%M%S).dump"

# O en formato SQL plano (legible)
pg_dump -U crm_prod_user \
  -d crm_prod \
  -f "crm_prod_$(date +%Y-%m-%d_%H%M%S).sql"

# Verificar
ls -lh /opt/ycc/crm/backups/
```

### PostgreSQL: Backup incremental (para crons)

```bash
# Crear script: /opt/ycc/crm/backup_pg.sh
cat > /opt/ycc/crm/backup_pg.sh << 'BASH_SCRIPT'
#!/bin/bash
set -e

BACKUP_DIR="/opt/ycc/crm/backups"
DB_USER="crm_prod_user"
DB_NAME="crm_prod"
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/crm_prod_$TIMESTAMP.dump"

# Crear backup
pg_dump -U "$DB_USER" -d "$DB_NAME" -F c -f "$BACKUP_FILE"

# Comprimir
gzip "$BACKUP_FILE"

# Mantener solo últimos 30 días
find "$BACKUP_DIR" -name "crm_prod_*.dump.gz" -mtime +30 -delete

echo "Backup completado: $BACKUP_FILE.gz"
BASH_SCRIPT

chmod +x /opt/ycc/crm/backup_pg.sh
```

### Agregar a crontab

```bash
# Editar cron de user ycc
sudo -u ycc crontab -e

# Agregar línea:
# Diariamente a las 02:00 AM
0 2 * * * /opt/ycc/crm/backup_pg.sh >> /opt/ycc/crm/logs/backup.log 2>&1
```

### Restaurar desde backup

```bash
# ⚠️ CUIDADO: Esto sobrescribe la BD actual

# Primero: Hacer backup de estado actual
pg_dump -U crm_prod_user -d crm_prod -f /tmp/crm_before_restore.sql

# Descomprimir si es necesario
gunzip -c /opt/ycc/crm/backups/crm_prod_2026-04-20_020000.dump.gz > /tmp/restore.dump

# Detener el backend
sudo systemctl stop ycc-crm-backend

# Restaurar
pg_restore -U crm_prod_user -d crm_prod -c /tmp/restore.dump

# Reiniciar backend
sudo systemctl start ycc-crm-backend

# Verificar
sudo systemctl status ycc-crm-backend
```

### Backup de archivos (Frontend build, config)

```bash
# Backup incremental del directorio /opt/ycc/crm
tar -czf /opt/ycc/crm/backups/crm_full_$(date +%Y-%m-%d_%H%M%S).tar.gz \
  --exclude=node_modules \
  --exclude=venv \
  --exclude=.git \
  --exclude=dist \
  /opt/ycc/crm/
```

---

## Actualización de versión

### Flujo general

```bash
# 1. Hacer backup de BD actual
cd /opt/ycc/crm/backups
pg_dump -U crm_prod_user -d crm_prod -f pre_update_$(date +%Y-%m-%d).sql

# 2. Detener backend
sudo systemctl stop ycc-crm-backend

# 3. Actualizar repositorio backend
cd /opt/ycc/crm/backend
git fetch origin
git checkout main
git pull origin main

# 4. Actualizar dependencias Python
source venv/bin/activate
pip install -e ".[test]" --upgrade

# 5. Reiniciar backend
sudo systemctl start ycc-crm-backend

# 6. Actualizar repositorio frontend
cd /opt/ycc/crm/frontend
git fetch origin
git checkout main
git pull origin main

# 7. Instalar nuevas dependencias npm
npm ci

# 8. Build producción
npm run build

# 9. Recargar Nginx
sudo nginx -t
sudo systemctl reload nginx

# 10. Verificar
curl -I https://crm.microtv.ar/api/health
sudo systemctl status ycc-crm-backend
sudo journalctl -u ycc-crm-backend -n 20
```

### Con migraciones (si en futuro se agregan)

```bash
# Después del paso 4 (pip install):
# Si hay migraciones con Alembic (cuando se implemente):
# cd /opt/ycc/crm/backend
# source venv/bin/activate
# alembic upgrade head
```

---

## Rollback

### Rollback a versión anterior (sin cambios DB)

```bash
# 1. Anotar commit actual para poder recuperar si es necesario
cd /opt/ycc/crm/backend
CURRENT_COMMIT=$(git rev-parse HEAD)
echo "Commit actual: $CURRENT_COMMIT" >> /tmp/rollback_log.txt

# 2. Volver a commit anterior
git log --oneline | head -10  # Ver histórico
git checkout <COMMIT_HASH_ANTERIOR>

# 3. Reinstalar dependencias de esa versión
source venv/bin/activate
pip install -e ".[test]"

# 4. Reiniciar backend
sudo systemctl restart ycc-crm-backend

# 5. Frontend (si hubo cambios)
cd /opt/ycc/crm/frontend
git checkout <COMMIT_ANTERIOR>
npm ci
npm run build
sudo systemctl reload nginx

# 6. Verificar
sudo systemctl status ycc-crm-backend
curl -I https://crm.microtv.ar/api/health
```

### Rollback con restauración de DB (si migración fue destructiva)

```bash
# ⚠️ SOLO SI LA MIGRACIÓN CAMBIÓ ESTRUCTURA DB

# 1. Detener backend
sudo systemctl stop ycc-crm-backend

# 2. Restaurar DB desde backup pre-update
pg_restore -U crm_prod_user -d crm_prod -c /opt/ycc/crm/backups/pre_update_2026-04-20.sql

# 3. Revertir código
cd /opt/ycc/crm/backend
git checkout <COMMIT_ANTERIOR>
source venv/bin/activate
pip install -e ".[test]"

# 4. Reiniciar backend
sudo systemctl start ycc-crm-backend

# 5. Verificar que DB está sincronizada
sudo systemctl status ycc-crm-backend
```

---

## Troubleshooting

### Backend no levanta

**Síntoma:** `sudo systemctl status ycc-crm-backend` muestra `failed`

**Pasos:**

```bash
# 1. Ver logs de error
sudo journalctl -u ycc-crm-backend -n 100

# 2. Validar .env
cat /opt/ycc/crm/backend/.env | grep DATABASE_URL
# Verificar que URL es válida y credentials correctas

# 3. Validar conexión a DB
cd /opt/ycc/crm/backend
source venv/bin/activate
python -c "from crm_backend.db.session import SessionLocal; s = SessionLocal(); print('OK')"

# 4. Verificar que el módulo FastAPI existe
python -c "from crm_backend.main import app; print(app)"

# 5. Probar uvicorn manualmente
/opt/ycc/crm/backend/venv/bin/uvicorn crm_backend.main:app --host 127.0.0.1 --port 8010
# Si levanta, el problema está en systemd o .env

# 6. Verificar permisos
ls -la /opt/ycc/crm/backend/.env
sudo ls -la /opt/ycc/crm/backend/.env
# Debe ser legible por user ycc
```

### Error de conexión a BD

**Síntoma:** `could not connect to server: Connection refused`

**Pasos:**

```bash
# 1. Verificar que PostgreSQL está corriendo
sudo systemctl status postgresql

# 2. Validar credenciales
psql -U crm_prod_user -d crm_prod -h localhost -c "SELECT 1;"
# Si falla: contraseña incorrecta o usuario no existe

# 3. Validar que el puerto de BD es correcto (5432 por defecto)
sudo ss -tlnp | grep postgres

# 4. Validar pg_hba.conf
sudo nano /etc/postgresql/16/main/pg_hba.conf
# Debe tener línea para crm_prod_user

# 5. Reiniciar PostgreSQL
sudo systemctl restart postgresql
sudo systemctl status postgresql
```

### Frontend no carga, error 502 Bad Gateway

**Síntoma:** `https://crm.microtv.ar` devuelve 502

**Pasos:**

```bash
# 1. Verificar que backend está corriendo en localhost:8010
sudo systemctl status ycc-crm-backend
sudo ss -tlnp | grep 8010

# 2. Verificar logs de Nginx
sudo tail -50 /opt/ycc/crm/logs/nginx/crm_error.log

# 3. Verificar que proxy_pass está correcto en Nginx
sudo grep "proxy_pass" /etc/nginx/sites-enabled/crm.microtv.ar

# 4. Validar sintaxis Nginx
sudo nginx -t

# 5. Reiniciar Nginx
sudo systemctl restart nginx

# 6. Probar conectividad backend
curl -I http://127.0.0.1:8010/api/health
# Si falla: backend está caído
```

### API devuelve CORS error

**Síntoma:** Browser console: `Cross-Origin Request Blocked`

**Pasos:**

```bash
# 1. Verificar CORS_ORIGINS en .env
cat /opt/ycc/crm/backend/.env | grep CORS

# Debe incluir el dominio del frontend (https://crm.microtv.ar)

# 2. Restartear backend si se cambió .env
sudo systemctl restart ycc-crm-backend

# 3. Verificar en response headers
curl -I https://crm.microtv.ar/api/health | grep "Access-Control"

# 4. Si CORS_ORIGIN_REGEX está en uso, validar que la regex es correcta
```

### PWA no es instalable

**Síntoma:** No aparece el botón "Instalar" o no funciona

**Pasos:**

```bash
# 1. Verificar que manifest.webmanifest existe
curl -I https://crm.microtv.ar/manifest.webmanifest
# Debe devolver 200

# 2. Verificar que HTTPS está habilitado
# PWA requiere HTTPS (o localhost)

# 3. Verificar que service worker está registrado
curl -I https://crm.microtv.ar/ngsw.json
# Debe devolver 200

# 4. En DevTools del navegador:
# - Application → Manifest: debe mostrar datos válidos
# - Application → Service Workers: debe mostrar "activated"

# 5. Verificar que index.html incluye link al manifest
curl https://crm.microtv.ar | grep "manifest"
```

### Service Worker no actualiza

**Síntoma:** Cambios de frontend no aparecen después de deploy

**Pasos:**

```bash
# 1. Verificar que ngsw.json se regeneró
stat /opt/ycc/crm/frontend/dist/browser/ngsw.json

# 2. Verificar que Nginx NO está cacheando ngsw.json
sudo grep -A 10 "ngsw.json" /etc/nginx/sites-enabled/crm.microtv.ar

# Debe tener:
# add_header Cache-Control "no-store, no-cache, must-revalidate";

# 3. En navegador: Hard refresh (Cmd+Shift+R en Mac, Ctrl+Shift+R en Windows/Linux)

# 4. Limpiar Service Worker
# DevTools → Application → Service Workers → Unregister → Hard refresh
```

### Errores de permisos de archivos

**Síntoma:** `Permission denied` en logs

**Pasos:**

```bash
# 1. Verificar propiedad de /opt/ycc/crm
ls -la /opt/ycc/crm

# Debe ser propiedad de user ycc
sudo chown -R ycc:ycc /opt/ycc/crm

# 2. Verificar permisos directorios
sudo chmod 755 /opt/ycc/crm
sudo chmod 755 /opt/ycc/crm/backend
sudo chmod 755 /opt/ycc/crm/frontend
sudo chmod 755 /opt/ycc/crm/logs
sudo chmod 755 /opt/ycc/crm/backups

# 3. Verificar permisos .env
sudo chmod 600 /opt/ycc/crm/backend/.env
# Solo user ycc puede leer (contiene passwords)

# 4. Reiniciar servicios
sudo systemctl restart ycc-crm-backend
sudo systemctl restart nginx
```

### Puerto 8010 ya en uso

**Síntoma:** `Address already in use`

**Pasos:**

```bash
# 1. Identificar qué proceso usa el puerto
sudo ss -tlnp | grep 8010

# 2. Si es un uvicorn viejo, matarlo
sudo kill -9 <PID>

# 3. Reiniciar backend
sudo systemctl restart ycc-crm-backend

# 4. Si persiste, cambiar puerto en .env (no recomendado en prod)
# PORT=8011
```

### Alto consumo de CPU/memoria

**Síntoma:** Backend consumiendo 80%+ CPU

**Pasos:**

```bash
# 1. Ver logs de backend
sudo journalctl -u ycc-crm-backend -f
# Buscar queries lentas, loops infinitos, etc.

# 2. Aumentar workers de uvicorn (si aplica)
# En /etc/systemd/system/ycc-crm-backend.service:
# --workers 8  (aumentar de 4)
sudo systemctl daemon-reload
sudo systemctl restart ycc-crm-backend

# 3. Analizar BD
# Ver queries lentas en PostgreSQL:
sudo -u postgres psql -d crm_prod -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# 4. Consultar logs de Nginx
sudo tail -100 /opt/ycc/crm/logs/nginx/crm_access.log
# Buscar requests que tarden mucho (última columna)
```

### Problema de certificado SSL

**Síntoma:** `curl: (60) SSL certificate problem`

**Pasos:**

```bash
# 1. Verificar que cert existe
sudo ls -la /etc/letsencrypt/live/crm.microtv.ar/

# 2. Renovar certificado manualmente
sudo certbot renew --force-renewal -d crm.microtv.ar

# 3. Verificar fecha de expiración
sudo openssl x509 -dates -noout -in /etc/letsencrypt/live/crm.microtv.ar/fullchain.pem

# 4. Ver errores de certbot
sudo journalctl -u certbot.service -n 50
```

---

## Apéndice A: Variables de entorno

```bash
# Backend (.env)
APP_NAME=MicroTV CRM Backend                                    # Nombre de la app
ENVIRONMENT=production                                           # Entorno (development/test/production)
HOST=127.0.0.1                                                   # Host (localhost en prod)
PORT=8010                                                        # Puerto FastAPI
DATABASE_URL=postgresql+psycopg://crm_prod_user:...@localhost:5432/crm_prod  # BD
CORS_ORIGINS=https://crm.microtv.ar                             # Dominios CORS
AUTH_BASE_URL=https://auth.microtv.ar                           # URL de auth externo
AUTH_JWT_SECRET=<CAMBIAR>                                        # Secret JWT compartido
AUTH_JWT_ISSUER=auth.microtv.ar                                  # Issuer JWT
AUTH_JWT_AUDIENCE=microtv-platform                               # Audience JWT
AUTO_PROVISION_CRM_ROLE=true                                     # Auto-crear rol local
DEFAULT_ADMIN_AUTH_ROLES=platform_admin,company_admin            # Roles admin
DEFAULT_DEPOSITO_AUTH_ROLES=company_operator                     # Roles depósito
DEFAULT_TECH_AUTH_ROLES=company_operator                         # Roles técnico

# Frontend (.env.production)
ANGULAR_APP_API_BASE_URL=https://crm.microtv.ar/api              # Base URL de API
ANGULAR_APP_AUTH_BASE_URL=https://auth.microtv.ar                # URL de auth
```

---

## Apéndice B: Comandos frecuentes

```bash
# Estado de servicios
sudo systemctl status postgresql ycc-crm-backend nginx

# Logs en tiempo real
sudo journalctl -u ycc-crm-backend -f
sudo tail -f /opt/ycc/crm/logs/nginx/crm_error.log

# Reinicio de servicios
sudo systemctl restart ycc-crm-backend
sudo systemctl reload nginx

# Validar conectividad
curl -I https://crm.microtv.ar/api/health
curl -I https://crm.microtv.ar

# Ver escucha de puertos
sudo ss -tlnp | grep 8010
sudo ss -tlnp | grep 5432

# Ver procesos Python
ps aux | grep uvicorn

# Ver logs de BD
sudo tail -100 /var/log/postgresql/postgresql-16-main.log
```

---

## Apéndice C: Glosario

- **ASGI:** Async Server Gateway Interface (FastAPI usa uvicorn como servidor ASGI)
- **JWT:** JSON Web Token (autenticación delegada a auth.microtv.ar)
- **SPA:** Single Page Application (Angular es una SPA)
- **SSR:** Server-Side Rendering (Angular genera también en dist/server/)
- **PWA:** Progressive Web App (instalable, service worker, offline)
- **systemd:** Gestor de servicios en Linux (PID 1, inicia/maneja servicios)
- **pg_dump/pg_restore:** Herramientas de backup/restore de PostgreSQL
- **Certbot:** Cliente Let's Encrypt para HTTPS automático
- **Nginx:** Reverse proxy, load balancer, web server
- **uvicorn:** Servidor ASGI liviano para FastAPI

---

## Apéndice D: Contactos y referencias

**Repositorio Backend:**  
`<URL_REPO_BACKEND>`

**Repositorio Frontend:**  
`<URL_REPO_FRONTEND>`

**Auth externo:**  
`https://auth.microtv.ar` (coordinar JWT_SECRET con equipo)

**Documentación:**
- FastAPI: https://fastapi.tiangolo.com/
- Angular: https://angular.io/docs
- SQLAlchemy: https://docs.sqlalchemy.org/
- PostgreSQL: https://www.postgresql.org/docs/16/
- Nginx: https://nginx.org/en/docs/
- Certbot: https://certbot.eff.org/docs/

---

**Versión:** 1.0  
**Última revisión:** 2026-04-24  
**Autor:** Senior DevOps / Platform Engineering
