ALTER TABLE public.tasks
    ADD COLUMN IF NOT EXISTS category_id UUID;

ALTER TABLE public.tickets
    ADD COLUMN IF NOT EXISTS category_id UUID;

CREATE INDEX IF NOT EXISTS idx_tasks_category_id ON public.tasks(category_id);
CREATE INDEX IF NOT EXISTS idx_tickets_category_id ON public.tickets(category_id);

DO $$
DECLARE
    fk_record RECORD;
BEGIN
    IF to_regclass('public.crm_categories') IS NULL THEN
        RETURN;
    END IF;

    FOR fk_record IN
        SELECT con.conname, con.conrelid::regclass AS table_name
        FROM pg_constraint con
        JOIN pg_attribute att
          ON att.attrelid = con.conrelid
         AND att.attnum = ANY(con.conkey)
        WHERE con.contype = 'f'
          AND con.conrelid IN ('public.tasks'::regclass, 'public.tickets'::regclass)
          AND att.attname = 'category_id'
          AND con.confrelid <> 'public.crm_categories'::regclass
    LOOP
        EXECUTE format('ALTER TABLE %s DROP CONSTRAINT IF EXISTS %I', fk_record.table_name, fk_record.conname);
    END LOOP;
END $$;

UPDATE public.tasks task_row
SET category_id = NULL
WHERE category_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM public.crm_categories category_row
      WHERE category_row.category_id = task_row.category_id
  );

UPDATE public.tickets ticket_row
SET category_id = NULL
WHERE category_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM public.crm_categories category_row
      WHERE category_row.category_id = ticket_row.category_id
  );

DO $$
BEGIN
    IF to_regclass('public.crm_categories') IS NULL THEN
        RETURN;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint con
        JOIN pg_attribute att
          ON att.attrelid = con.conrelid
         AND att.attnum = ANY(con.conkey)
        WHERE con.contype = 'f'
          AND con.conrelid = 'public.tasks'::regclass
          AND att.attname = 'category_id'
          AND con.confrelid = 'public.crm_categories'::regclass
    ) THEN
        ALTER TABLE public.tasks
            ADD CONSTRAINT fk_tasks_category_crm_categories
            FOREIGN KEY (category_id) REFERENCES public.crm_categories(category_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint con
        JOIN pg_attribute att
          ON att.attrelid = con.conrelid
         AND att.attnum = ANY(con.conkey)
        WHERE con.contype = 'f'
          AND con.conrelid = 'public.tickets'::regclass
          AND att.attname = 'category_id'
          AND con.confrelid = 'public.crm_categories'::regclass
    ) THEN
        ALTER TABLE public.tickets
            ADD CONSTRAINT fk_tickets_category_crm_categories
            FOREIGN KEY (category_id) REFERENCES public.crm_categories(category_id);
    END IF;
END $$;
