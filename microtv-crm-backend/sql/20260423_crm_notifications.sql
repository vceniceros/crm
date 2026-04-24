-- In-app notifications schema extension
-- Date: 2026-04-23

CREATE TABLE IF NOT EXISTS crm_notifications (
    notification_id UUID PRIMARY KEY,
    recipient_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE CASCADE,
    notification_type VARCHAR(80) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    entity_type VARCHAR(40) NULL,
    entity_id VARCHAR(36) NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    read_at TIMESTAMPTZ NULL,
    metadata JSONB NULL
);

CREATE INDEX IF NOT EXISTS idx_crm_notifications_recipient ON crm_notifications(recipient_crm_user_id);
CREATE INDEX IF NOT EXISTS idx_crm_notifications_type ON crm_notifications(notification_type);
CREATE INDEX IF NOT EXISTS idx_crm_notifications_is_read ON crm_notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_crm_notifications_created_at ON crm_notifications(created_at);
CREATE INDEX IF NOT EXISTS idx_crm_notifications_recipient_unread_created
    ON crm_notifications(recipient_crm_user_id, is_read, created_at DESC);
