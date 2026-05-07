#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$BACKEND_DIR/.env"

DB_URL=""
if [ -f "$ENV_FILE" ]; then
  DB_URL="$(grep -E '^DATABASE_URL=' "$ENV_FILE" | tail -n 1 | cut -d '=' -f 2- || true)"
  DB_URL="${DB_URL%\"}"
  DB_URL="${DB_URL#\"}"
  DB_URL="${DB_URL%\'}"
  DB_URL="${DB_URL#\'}"
fi

if [ -n "$DB_URL" ]; then
  # SQLAlchemy URL -> psql URL
  DB_URL="${DB_URL/postgresql+psycopg:/postgresql:}"
  PSQL=(psql -X -v ON_ERROR_STOP=1 "$DB_URL")
  echo "Usando DATABASE_URL de $ENV_FILE"
else
  # Fallback legacy values.
  PSQL=(psql -X -v ON_ERROR_STOP=1 -U ycc -h 127.0.0.1 -p 5432 -d crm)
  echo "DATABASE_URL no encontrado en $ENV_FILE; usando conexion fallback 127.0.0.1:5432/crm"
fi

echo "=== Iniciando migraciones de produccion ==="

"${PSQL[@]}" -c "SELECT current_database() AS db, current_user AS db_user, inet_server_addr() AS host, inet_server_port() AS port;"

run_migration() {
  local file="$1"
  echo "--- Aplicando: $file"
  "${PSQL[@]}" -f "$file"
  echo "    OK: $file"
}

constraint_exists() {
  local constraint_name="$1"
  "${PSQL[@]}" -t -A -c "SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '$constraint_name');" | tr -d '[:space:]'
}

run_migration "$SCRIPT_DIR/20260414_task_schema_v4_delta.sql"
if [ "$(constraint_exists 'chk_template_subtasks_next_assignment_policy')" = "true" ]; then
  echo "--- Saltando: $SCRIPT_DIR/20260414_task_schema_v4_1_hardening.sql (hardening ya aplicado)"
else
  run_migration "$SCRIPT_DIR/20260414_task_schema_v4_1_hardening.sql"
fi
run_migration "$SCRIPT_DIR/20260414_task_schema_v4_1_post_validation.sql"
run_migration "$SCRIPT_DIR/20260414_task_media_comment_link.sql"
run_migration "$SCRIPT_DIR/20260422_ticket_module.sql"
run_migration "$SCRIPT_DIR/20260423_crm_notifications.sql"
run_migration "$SCRIPT_DIR/20260427_ticket_arrival_comment.sql"
run_migration "$SCRIPT_DIR/20260428_notifications_seed.sql"
run_migration "$SCRIPT_DIR/20260430_ticket_profile_enhancements.sql"

echo ""
echo "=== Verificando estado final del schema ==="
verification_output="$("${PSQL[@]}" -t -A -F '|' -c "
SELECT
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='tickets' AND column_name='requires_video_evidence') AS col_video_evidence,
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='tickets' AND column_name='arrival_comment_id')      AS col_arrival_comment,
  EXISTS(SELECT 1 FROM information_schema.tables   WHERE table_name='crm_notifications')                                AS table_notifications,
  (SELECT count(*) FROM crm_roles WHERE is_active = TRUE)                                                               AS active_roles_count;
")"

echo "col_video_evidence|col_arrival_comment|table_notifications|active_roles_count"
echo "$verification_output"

if [[ "$verification_output" != true\|true\|true\|* ]]; then
  echo "ERROR: Verificacion final del schema invalida: $verification_output"
  exit 1
fi

echo "=== Migraciones completadas ==="
