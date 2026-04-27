# Production Deployment — auth.microtv.ar

## Prerequisites

| Component       | Minimum version |
|-----------------|-----------------|
| Ubuntu Server   | 22.04 LTS       |
| Python          | 3.12            |
| PostgreSQL      | 15              |
| rsync           | any             |

## Quick deploy

```bash
# Clone the repository on the server
git clone https://gitlab.ycc.com.ar/it-ycc/auth.microtv.ar.git
cd auth.microtv.ar

# Run the automated deployment
sudo bash deploy/deploy.sh
```

On first run the script will:

1. Create a `authmicrotv` system user (no shell, no home).
2. Copy the application to `/opt/auth.microtv.ar`.
3. Create `backend/.env` from `.env.example` — **you must edit it** before the service starts accepting real traffic.
4. Create a Python 3.12 virtual environment and install dependencies.
5. Run Alembic migrations against the configured database.
6. Install and start the `auth-microtv.service` systemd unit.
7. Run a health-check smoke test.

## Production .env

Edit `/opt/auth.microtv.ar/backend/.env`:

```ini
DATABASE_URL=postgresql+psycopg://authmicrotv:<password>@localhost/auth_microtv
JWT_SECRET=<random-64-char-string>
JWT_ALGORITHM=HS256
JWT_AUDIENCE=microtv-platform
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_MINUTES=10080
LOGIN_TICKET_EXPIRE_MINUTES=10
ENVIRONMENT=production
# Comma-separated — add every frontend origin that calls the API
ALLOWED_ORIGINS=https://saas.microtv.ar
```

Generate a strong JWT secret:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Service management

```bash
# Status
sudo systemctl status auth-microtv.service

# Restart after config changes
sudo systemctl restart auth-microtv.service

# Follow logs
sudo journalctl -fu auth-microtv.service

# Stop
sudo systemctl stop auth-microtv.service
```

## Reverse proxy (nginx)

The service listens on `127.0.0.1:8001`. Place an nginx virtual host in front:

```nginx
server {
    listen 443 ssl http2;
    server_name auth.microtv.ar;

    ssl_certificate     /etc/letsencrypt/live/auth.microtv.ar/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/auth.microtv.ar/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Updating

```bash
cd /path/to/auth.microtv.ar   # local clone
git pull origin main
sudo bash deploy/deploy.sh    # re-runs everything idempotently
```

The script preserves the existing `.env` — only code files are synced.

## PostgreSQL setup (one-time)

```bash
sudo -u postgres psql <<SQL
CREATE ROLE authmicrotv WITH LOGIN PASSWORD '<password>';
CREATE DATABASE auth_microtv OWNER authmicrotv;
SQL
```

Migrations are applied automatically by the deploy script.
