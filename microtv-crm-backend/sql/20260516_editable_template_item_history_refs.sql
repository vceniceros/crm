-- Allow editing templates after pedidos have been created from them.
-- Instantiated checklist rows keep their historical label/order/type, so this
-- template reference must be nullable when template checklist items are deleted.

BEGIN;

ALTER TABLE subtask_checklist_items
  ALTER COLUMN template_checklist_item_id DROP NOT NULL;

DO $$
DECLARE
  constraint_name text;
BEGIN
  FOR constraint_name IN
    SELECT con.conname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    JOIN pg_class refrel ON refrel.oid = con.confrelid
    JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = ANY(con.conkey)
    WHERE con.contype = 'f'
      AND rel.relname = 'subtask_checklist_items'
      AND refrel.relname = 'template_subtask_checklist_items'
      AND att.attname = 'template_checklist_item_id'
  LOOP
    EXECUTE format('ALTER TABLE subtask_checklist_items DROP CONSTRAINT %I', constraint_name);
  END LOOP;
END $$;

ALTER TABLE subtask_checklist_items
  ADD CONSTRAINT fk_subtask_checklist_items_template_item
  FOREIGN KEY (template_checklist_item_id)
  REFERENCES template_subtask_checklist_items(template_checklist_item_id)
  ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_subtask_checklist_items_template_item
  ON subtask_checklist_items(template_checklist_item_id);

COMMIT;
