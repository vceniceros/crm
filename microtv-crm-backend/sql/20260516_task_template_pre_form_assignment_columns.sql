-- Repair task template pre-form assignment columns.
-- Safe to run more than once.

BEGIN;

ALTER TABLE task_template_pre_forms
  ADD COLUMN IF NOT EXISTS assignment_role_key VARCHAR(50),
  ADD COLUMN IF NOT EXISTS assignment_crm_user_id UUID REFERENCES crm_users(crm_user_id);

UPDATE task_template_pre_forms
SET assignment_role_key = 'tecnico'
WHERE assignment_role_key IS NULL;

CREATE INDEX IF NOT EXISTS idx_task_template_pre_forms_assignment_role
  ON task_template_pre_forms(assignment_role_key);

CREATE INDEX IF NOT EXISTS idx_task_template_pre_forms_assignment_user
  ON task_template_pre_forms(assignment_crm_user_id);

COMMIT;
