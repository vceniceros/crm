-- DDL para tabla de reglas de notificacion
-- Necesaria para desbloquear seeds de notificaciones en entornos ya migrados
-- Fecha: 2026-05-11

CREATE TABLE IF NOT EXISTS crm_notification_rules (
    notification_rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_code           TEXT NOT NULL UNIQUE,
    label                TEXT NOT NULL,
    notify_assigned      BOOLEAN NOT NULL DEFAULT TRUE,
    notify_roles_json    JSONB NOT NULL DEFAULT '[]',
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
