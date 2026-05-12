-- Push subscriptions para notificaciones nativas (Web Push / VAPID)
-- Fecha: 2026-05-12

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    crm_user_id   UUID         NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE CASCADE,
    endpoint      TEXT         NOT NULL UNIQUE,
    p256dh        TEXT         NOT NULL,
    auth          TEXT         NOT NULL,
    user_agent    TEXT         NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_push_subscriptions_user
    ON push_subscriptions(crm_user_id);
