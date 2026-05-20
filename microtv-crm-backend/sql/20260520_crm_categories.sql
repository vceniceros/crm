CREATE TABLE IF NOT EXISTS crm_categories (
    category_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    category_type VARCHAR(50) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    default_role_id UUID REFERENCES crm_roles(crm_role_id),
    allows_scheduling BOOLEAN NOT NULL DEFAULT FALSE,
    schedule_period_type VARCHAR(30),
    schedule_interval_weeks INTEGER,
    schedule_weekdays_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    schedule_start_date DATE,
    schedule_end_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_crm_categories_name ON crm_categories(name);
CREATE INDEX IF NOT EXISTS ix_crm_categories_category_type ON crm_categories(category_type);
CREATE INDEX IF NOT EXISTS ix_crm_categories_default_role_id ON crm_categories(default_role_id);

INSERT INTO crm_categories (
    category_id,
    name,
    category_type,
    description,
    is_active,
    is_system,
    allows_scheduling
)
SELECT
    gen_random_uuid(),
    'Incidente',
    'operational',
    'Categoria general de incidentes (default del sistema).',
    TRUE,
    TRUE,
    FALSE
WHERE NOT EXISTS (
    SELECT 1
    FROM crm_categories
    WHERE LOWER(name) = LOWER('Incidente')
      AND category_type = 'operational'
)
ON CONFLICT DO NOTHING;

ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS category_id UUID REFERENCES crm_categories(category_id);

CREATE INDEX IF NOT EXISTS idx_tasks_category_id ON tasks(category_id);

ALTER TABLE tickets
    ADD COLUMN IF NOT EXISTS category_id UUID REFERENCES crm_categories(category_id);

CREATE INDEX IF NOT EXISTS idx_tickets_category_id ON tickets(category_id);
