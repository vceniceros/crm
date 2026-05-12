#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$BACKEND_DIR/.env"

DB_URL=""
DB_SOURCE=""
USE_FALLBACK="false"

if [ -n "${MIGRATION_DATABASE_URL:-}" ]; then
  DB_URL="$MIGRATION_DATABASE_URL"
  DB_SOURCE='MIGRATION_DATABASE_URL'
elif [ -f "$ENV_FILE" ]; then
  DB_URL="$(grep -E '^[[:space:]]*DATABASE_URL[[:space:]]*=' "$ENV_FILE" | tail -n 1 | sed -E 's/^[[:space:]]*DATABASE_URL[[:space:]]*=[[:space:]]*//' || true)"
  DB_SOURCE="$ENV_FILE"
  DB_URL="${DB_URL%\"}"
  DB_URL="${DB_URL#\"}"
  DB_URL="${DB_URL%\'}"
  DB_URL="${DB_URL#\'}"
fi

if [ -n "$DB_URL" ]; then
  case "$DB_URL" in
    postgresql+psycopg://*)
      DB_URL="${DB_URL/postgresql+psycopg:\/\//postgresql://}"
      ;;
    postgresql://*)
      ;;
    postgres://*)
      DB_URL="${DB_URL/postgres:\/\//postgresql://}"
      ;;
    sqlite://*|sqlite3://*)
      echo "WARNING: DATABASE_URL apunta a SQLite en $DB_SOURCE."
      echo "WARNING: Se usara fallback PostgreSQL (127.0.0.1:5432/crm) para esta migracion."
      USE_FALLBACK="true"
      ;;
    *)
      if [ "$DB_SOURCE" = "MIGRATION_DATABASE_URL" ]; then
        echo "ERROR: MIGRATION_DATABASE_URL tiene un esquema no soportado."
        echo "Soportados: postgresql+psycopg://, postgresql://, postgres://"
        exit 1
      fi

      echo "WARNING: DATABASE_URL tiene un esquema no soportado en $DB_SOURCE."
      echo "WARNING: Se usara fallback PostgreSQL (127.0.0.1:5432/crm) para esta migracion."
      USE_FALLBACK="true"
      ;;
  esac

  if [ "$USE_FALLBACK" != "true" ]; then
    PSQL=(psql -X -v ON_ERROR_STOP=1 "$DB_URL")
    echo "Usando DATABASE_URL de $DB_SOURCE"
  fi
fi

if [ "$USE_FALLBACK" = "true" ] || [ -z "$DB_URL" ]; then
  PSQL=(psql -X -v ON_ERROR_STOP=1 -U ycc -h 127.0.0.1 -p 5432 -d crm)
  if [ "$USE_FALLBACK" = "false" ]; then
    echo "DATABASE_URL no encontrado en $ENV_FILE; usando conexion fallback 127.0.0.1:5432/crm"
  fi
fi

is_truthy() {
  local value="${1:-}"
  case "$value" in
    t|true|1|y|yes)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

ensure_migration_tracking() {
  "${PSQL[@]}" -c "
    CREATE TABLE IF NOT EXISTS crm_schema_migrations (
      migration_name TEXT PRIMARY KEY,
      applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
  "
}

is_migration_applied() {
  local migration_name="$1"
  "${PSQL[@]}" -t -A -c "SELECT EXISTS (SELECT 1 FROM crm_schema_migrations WHERE migration_name = '$migration_name');" | tr -d '[:space:]'
}

record_migration() {
  local migration_name="$1"
  "${PSQL[@]}" -c "
    INSERT INTO crm_schema_migrations (migration_name)
    VALUES ('$migration_name')
    ON CONFLICT (migration_name) DO NOTHING;
  " >/dev/null
}

run_migration() {
  local file="$1"
  local file_name
  local output_file

  file_name="$(basename "$file")"

  if is_truthy "$(is_migration_applied "$file_name")"; then
    echo "--- Saltando: $file_name (ya registrada en crm_schema_migrations)"
    return
  fi

  output_file="$(mktemp)"
  echo "--- Aplicando: $file_name"

  if "${PSQL[@]}" -f "$file" >"$output_file" 2>&1; then
    record_migration "$file_name"
    echo "    OK: $file_name"
    rm -f "$output_file"
    return
  fi

  if grep -Eqi "already exists|duplicate key value|column .* already exists|relation .* already exists|constraint .* already exists" "$output_file"; then
    echo "    WARNING: $file_name devolvio un error de objeto existente; se registra como aplicada para evitar reintentos."
    sed 's/^/      /' "$output_file"
    record_migration "$file_name"
    rm -f "$output_file"
    return
  fi

  echo "ERROR aplicando $file_name"
  sed 's/^/      /' "$output_file"
  rm -f "$output_file"
  exit 1
}

echo "=== Iniciando migraciones de produccion ==="
"${PSQL[@]}" -c "SELECT current_database() AS db, current_user AS db_user, inet_server_addr() AS host, inet_server_port() AS port;"

ensure_migration_tracking

shopt -s nullglob
migration_files=("$SCRIPT_DIR"/*.sql)
if [ ${#migration_files[@]} -eq 0 ]; then
  echo "ERROR: No se encontraron archivos .sql en $SCRIPT_DIR"
  exit 1
fi

IFS=$'\n' migration_files=($(printf '%s\n' "${migration_files[@]}" | sort))
unset IFS

for migration_file in "${migration_files[@]}"; do
  run_migration "$migration_file"
done

echo ""
echo "=== Verificando estado final del schema ==="
verification_output="$("${PSQL[@]}" -t -A -F '|' -c "
SELECT
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='tasks' AND column_name='requires_video_evidence') AS task_col_video_evidence,
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='tasks' AND column_name='arrival_comment_id')      AS task_col_arrival_comment,
  EXISTS(SELECT 1 FROM information_schema.tables   WHERE table_name='task_satisfaction_forms')                         AS table_task_satisfaction_forms,
  EXISTS(SELECT 1 FROM information_schema.tables   WHERE table_name='task_pre_form_instances')                         AS table_task_pre_form_instances,
  EXISTS(SELECT 1 FROM information_schema.tables   WHERE table_name='push_subscriptions')                              AS table_push_subscriptions,
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='inventory_products' AND column_name='minimum_stock') AS inv_col_minimum_stock,
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='inventory_products' AND column_name='shelf_id')      AS inv_col_shelf_id,
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='inventory_products' AND column_name='shelf_height')  AS inv_col_shelf_height,
  (SELECT count(*) FROM crm_roles WHERE is_active = TRUE)                                                              AS active_roles_count;
")"

echo "task_col_video_evidence|task_col_arrival_comment|table_task_satisfaction_forms|table_task_pre_form_instances|table_push_subscriptions|inv_col_minimum_stock|inv_col_shelf_id|inv_col_shelf_height|active_roles_count"
echo "$verification_output"

if [[ "$verification_output" != true\|true\|true\|true\|true\|true\|true\|true\|* ]]; then
  IFS='|' read -r col_video col_arrival table_satisfaction table_preform table_push inv_col_minimum_stock inv_col_shelf_id inv_col_shelf_height active_roles <<< "$verification_output"
  if ! is_truthy "$col_video" || ! is_truthy "$col_arrival" || ! is_truthy "$table_satisfaction" || ! is_truthy "$table_preform" || ! is_truthy "$table_push" || ! is_truthy "$inv_col_minimum_stock" || ! is_truthy "$inv_col_shelf_id" || ! is_truthy "$inv_col_shelf_height"; then
    echo "ERROR: Verificacion final del schema invalida: $verification_output"
    exit 1
  fi
fi

echo "=== Migraciones completadas ==="
