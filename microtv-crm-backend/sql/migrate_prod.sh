#!/usr/bin/env bash
set -euo pipefail

PSQL="psql -U ycc -h 127.0.0.1 -p 5432 -d crm"

echo "=== Iniciando migraciones de produccion ==="

run_migration() {
  local file="$1"
  echo "--- Aplicando: $file"
  $PSQL -f "$file"
  echo "    OK: $file"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

run_migration "$SCRIPT_DIR/20260414_task_schema_v4_delta.sql"
run_migration "$SCRIPT_DIR/20260414_task_schema_v4_1_hardening.sql"
run_migration "$SCRIPT_DIR/20260414_task_schema_v4_1_post_validation.sql"
run_migration "$SCRIPT_DIR/20260414_task_media_comment_link.sql"
run_migration "$SCRIPT_DIR/20260422_ticket_module.sql"
run_migration "$SCRIPT_DIR/20260423_crm_notifications.sql"
run_migration "$SCRIPT_DIR/20260427_ticket_arrival_comment.sql"
run_migration "$SCRIPT_DIR/20260428_notifications_seed.sql"
run_migration "$SCRIPT_DIR/20260430_ticket_profile_enhancements.sql"

echo ""
echo "=== Verificando estado final del schema ==="
$PSQL -c "
SELECT
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='tickets' AND column_name='requires_video_evidence') AS col_video_evidence,
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='tickets' AND column_name='arrival_comment_id')      AS col_arrival_comment,
  EXISTS(SELECT 1 FROM information_schema.tables   WHERE table_name='crm_notifications')                                AS table_notifications,
  (SELECT count(*) FROM crm_roles WHERE is_active = TRUE)                                                               AS active_roles_count;
"

echo "=== Migraciones completadas ==="
