ALTER TABLE public.crm_categories
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS is_system BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS default_role_id UUID,
    ADD COLUMN IF NOT EXISTS allows_scheduling BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS schedule_period_type VARCHAR(30),
    ADD COLUMN IF NOT EXISTS schedule_interval_weeks INTEGER,
    ADD COLUMN IF NOT EXISTS schedule_weekdays_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS schedule_start_date DATE,
    ADD COLUMN IF NOT EXISTS schedule_end_date DATE,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

DO $$
DECLARE
    fk_record RECORD;
BEGIN
    FOR fk_record IN
        SELECT con.conname
        FROM pg_constraint con
        JOIN pg_attribute att
          ON att.attrelid = con.conrelid
         AND att.attnum = ANY(con.conkey)
        WHERE con.contype = 'f'
          AND con.conrelid = 'public.crm_categories'::regclass
          AND att.attname = 'default_role_id'
          AND con.confrelid <> 'public.crm_roles'::regclass
    LOOP
        EXECUTE format('ALTER TABLE public.crm_categories DROP CONSTRAINT IF EXISTS %I', fk_record.conname);
    END LOOP;

    UPDATE public.crm_categories category_row
    SET default_role_id = NULL
    WHERE default_role_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM public.crm_roles role_row
          WHERE role_row.crm_role_id = category_row.default_role_id
      );

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint con
        JOIN pg_attribute att
          ON att.attrelid = con.conrelid
         AND att.attnum = ANY(con.conkey)
        WHERE con.contype = 'f'
          AND con.conrelid = 'public.crm_categories'::regclass
          AND att.attname = 'default_role_id'
          AND con.confrelid = 'public.crm_roles'::regclass
    ) THEN
        ALTER TABLE public.crm_categories
            ADD CONSTRAINT fk_crm_categories_default_role
            FOREIGN KEY (default_role_id) REFERENCES public.crm_roles(crm_role_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_crm_categories_name ON public.crm_categories(name);
CREATE INDEX IF NOT EXISTS ix_crm_categories_category_type ON public.crm_categories(category_type);
CREATE INDEX IF NOT EXISTS ix_crm_categories_default_role_id ON public.crm_categories(default_role_id);

INSERT INTO public.crm_categories (
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
    FROM public.crm_categories
    WHERE LOWER(name) = LOWER('Incidente')
      AND category_type = 'operational'
)
ON CONFLICT DO NOTHING;
