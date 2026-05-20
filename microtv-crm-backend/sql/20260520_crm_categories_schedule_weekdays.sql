ALTER TABLE crm_categories
    ADD COLUMN IF NOT EXISTS schedule_weekdays_json JSONB NOT NULL DEFAULT '[]'::jsonb;
