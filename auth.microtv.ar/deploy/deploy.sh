#!/usr/bin/env bash
# deploy.sh — Deploy auth.microtv.ar to a production Ubuntu server.
# Usage:  sudo bash deploy.sh
# Expects to be run from the repository root (where this script lives).
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
APP_NAME="auth-microtv"
APP_USER="authmicrotv"
INSTALL_DIR="/opt/microtv/auth.microtv.ar"
BACKEND_DIR="${INSTALL_DIR}/backend"
VENV_DIR="${BACKEND_DIR}/venv"
SERVICE_FILE="auth-microtv.service"
PYTHON="python3.12"

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
    echo "ERROR: This script must be run as root (sudo)." >&2
    exit 1
fi

if ! command -v "${PYTHON}" &>/dev/null; then
    echo "ERROR: ${PYTHON} not found. Install it first:" >&2
    echo "  apt install software-properties-common" >&2
    echo "  add-apt-repository ppa:deadsnakes/ppa" >&2
    echo "  apt update && apt install python3.12 python3.12-venv python3.12-dev" >&2
    exit 1
fi

if ! command -v psql &>/dev/null; then
    echo "ERROR: psql not found. Install postgresql-client:" >&2
    echo "  apt install postgresql-client" >&2
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Deploying ${APP_NAME} from ${REPO_ROOT}"

# ---------------------------------------------------------------------------
# 1. System user
# ---------------------------------------------------------------------------
if ! id "${APP_USER}" &>/dev/null; then
    echo "==> Creating system user ${APP_USER}"
    useradd --system --shell /usr/sbin/nologin --home-dir "${INSTALL_DIR}" "${APP_USER}"
fi

# ---------------------------------------------------------------------------
# 2. Install directory
# ---------------------------------------------------------------------------
echo "==> Syncing application files to ${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}"
rsync -a --delete \
    --exclude=".git" \
    --exclude="venv" \
    --exclude=".venv" \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    --exclude=".pytest_cache" \
    --exclude="*.egg-info" \
    --exclude="backend/.env" \
    "${REPO_ROOT}/" "${INSTALL_DIR}/"

# ---------------------------------------------------------------------------
# 3. Environment file
# ---------------------------------------------------------------------------
if [[ ! -f "${BACKEND_DIR}/.env" ]]; then
    echo "==> Creating .env from .env.example (EDIT before first start)"
    cp "${BACKEND_DIR}/.env.example" "${BACKEND_DIR}/.env"
    chmod 600 "${BACKEND_DIR}/.env"
    chown "${APP_USER}:${APP_USER}" "${BACKEND_DIR}/.env"
    echo ""
    echo "  *** IMPORTANT ***"
    echo "  Edit ${BACKEND_DIR}/.env with production values:"
    echo "    DATABASE_URL, JWT_SECRET, ENVIRONMENT=production"
    echo ""
else
    echo "==> .env already exists — keeping current values"
fi

# ---------------------------------------------------------------------------
# 4. Python virtual environment & dependencies
# ---------------------------------------------------------------------------
echo "==> Setting up virtual environment"
if [[ ! -d "${VENV_DIR}" ]]; then
    "${PYTHON}" -m venv "${VENV_DIR}"
fi
"${VENV_DIR}/bin/pip" install --upgrade pip setuptools wheel -q
"${VENV_DIR}/bin/pip" install -e "${BACKEND_DIR}" -q
echo "   Installed packages:"
"${VENV_DIR}/bin/pip" list --format=columns 2>/dev/null | head -20 || true

# ---------------------------------------------------------------------------
# 5. Database migrations
# ---------------------------------------------------------------------------
echo "==> Running Alembic migrations"
cd "${BACKEND_DIR}"
"${VENV_DIR}/bin/alembic" upgrade head
cd "${REPO_ROOT}"

# ---------------------------------------------------------------------------
# 6. Ownership
# ---------------------------------------------------------------------------
echo "==> Setting ownership to ${APP_USER}"
chown -R "${APP_USER}:${APP_USER}" "${INSTALL_DIR}"

# ---------------------------------------------------------------------------
# 7. systemd service
# ---------------------------------------------------------------------------
echo "==> Installing systemd service"
cp "${INSTALL_DIR}/deploy/${SERVICE_FILE}" "/etc/systemd/system/${SERVICE_FILE}"
systemctl daemon-reload
systemctl enable "${SERVICE_FILE}"
systemctl restart "${SERVICE_FILE}"
sleep 2

if systemctl is-active --quiet "${SERVICE_FILE}"; then
    echo "==> Service is running"
    systemctl status "${SERVICE_FILE}" --no-pager -l
else
    echo "ERROR: Service failed to start. Check logs:" >&2
    echo "  journalctl -u ${SERVICE_FILE} -n 40 --no-pager" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# 8. Smoke test
# ---------------------------------------------------------------------------
echo ""
echo "==> Smoke test: GET http://127.0.0.1:8001/health"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/health || true)
if [[ "${HTTP_CODE}" == "200" ]]; then
    echo "   Health check passed (HTTP ${HTTP_CODE})"
else
    echo "   WARNING: Health check returned HTTP ${HTTP_CODE}"
fi

echo ""
echo "=========================================="
echo " Deployment complete."
echo " Service : systemctl status ${SERVICE_FILE}"
echo " Logs    : journalctl -fu ${SERVICE_FILE}"
echo " Config  : ${BACKEND_DIR}/.env"
echo "=========================================="
