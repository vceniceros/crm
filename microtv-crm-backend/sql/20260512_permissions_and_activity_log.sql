-- =============================================================================
-- 20260512_permissions_and_activity_log.sql
-- Sistema unificado de permisos por rol + overrides por usuario + log de actividad
-- =============================================================================

-- ─── crm_role_permissions ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crm_role_permissions (
    role_permission_id  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_key            VARCHAR(50) NOT NULL,
    permission_code     VARCHAR(100) NOT NULL,
    is_granted          BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_crm_role_permission UNIQUE (role_key, permission_code)
);

CREATE INDEX IF NOT EXISTS idx_crm_role_permissions_role_key
    ON crm_role_permissions (role_key);

-- ─── crm_user_permissions ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crm_user_permissions (
    user_permission_id      UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    crm_user_id             UUID        NOT NULL
                                REFERENCES crm_users (crm_user_id)
                                ON DELETE CASCADE,
    permission_code         VARCHAR(100) NOT NULL,
    is_granted              BOOLEAN     NOT NULL DEFAULT TRUE,
    granted_by_crm_user_id  UUID
                                REFERENCES crm_users (crm_user_id)
                                ON DELETE SET NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_crm_user_permission UNIQUE (crm_user_id, permission_code)
);

CREATE INDEX IF NOT EXISTS idx_crm_user_permissions_user
    ON crm_user_permissions (crm_user_id);

-- ─── activity_log ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activity_log (
    activity_log_id     UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_crm_user_id   UUID
                            REFERENCES crm_users (crm_user_id)
                            ON DELETE SET NULL,
    event_code          VARCHAR(100) NOT NULL,
    entity_type         VARCHAR(50),
    entity_id           VARCHAR(36),
    entity_label        VARCHAR(255),
    summary             TEXT,
    payload_json        JSONB       NOT NULL DEFAULT '{}',
    ip_address          VARCHAR(45),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_log_created_at
    ON activity_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_log_actor
    ON activity_log (actor_crm_user_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_event_code
    ON activity_log (event_code);
CREATE INDEX IF NOT EXISTS idx_activity_log_entity
    ON activity_log (entity_type, entity_id);

-- ─── activity_log_archive ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activity_log_archive (
    LIKE activity_log INCLUDING DEFAULTS INCLUDING CONSTRAINTS,
    archived_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_log_archive_created_at
    ON activity_log_archive (created_at DESC);

-- ─── Seeds de permisos por defecto ───────────────────────────────────────────
INSERT INTO crm_role_permissions (role_key, permission_code, is_granted) VALUES
    ('admin',     'stock.manage',         TRUE),
    ('admin',     'stock.delete_product', TRUE),
    ('admin',     'ticket.reassign',      TRUE),
    ('admin',     'order.reassign',       TRUE),
    ('admin',     'comment.delete',       TRUE),
    ('deposito',  'stock.manage',         TRUE),
    ('deposito',  'stock.delete_product', FALSE),
    ('ejecutivo', 'ticket.reassign',      TRUE),
    ('ejecutivo', 'order.reassign',       TRUE)
ON CONFLICT (role_key, permission_code) DO NOTHING;
