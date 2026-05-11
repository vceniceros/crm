-- Task module extension:
-- - arrival/video gating on templates/tasks
-- - richer task comment typing with location binding
-- - task satisfaction forms
-- - task pre-form definitions and submissions

BEGIN;

ALTER TABLE task_templates
  ADD COLUMN IF NOT EXISTS requires_arrival_comment BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS requires_video_evidence BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS requires_pre_form BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS requires_arrival_comment BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS requires_video_evidence BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS arrival_registered_at TIMESTAMPTZ NULL,
  ADD COLUMN IF NOT EXISTS arrival_comment_id UUID NULL;

ALTER TABLE task_comments
  ADD COLUMN IF NOT EXISTS location_id UUID NULL REFERENCES locations(location_id) ON DELETE SET NULL;

ALTER TABLE template_subtasks
  ADD COLUMN IF NOT EXISTS subtask_type VARCHAR(50) NOT NULL DEFAULT 'standard';

ALTER TABLE subtasks
  ADD COLUMN IF NOT EXISTS subtask_type VARCHAR(50) NOT NULL DEFAULT 'standard';

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_tasks_arrival_comment'
  ) THEN
    ALTER TABLE tasks
      ADD CONSTRAINT fk_tasks_arrival_comment
      FOREIGN KEY (arrival_comment_id)
      REFERENCES task_comments(task_comment_id)
      ON DELETE SET NULL;
  END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_tasks_arrival_comment_id ON tasks(arrival_comment_id);
CREATE INDEX IF NOT EXISTS idx_tasks_requires_arrival_comment ON tasks(requires_arrival_comment);
CREATE INDEX IF NOT EXISTS idx_tasks_requires_video_evidence ON tasks(requires_video_evidence);
CREATE INDEX IF NOT EXISTS idx_task_comments_location_id ON task_comments(location_id);
CREATE INDEX IF NOT EXISTS idx_template_subtasks_subtask_type ON template_subtasks(subtask_type);
CREATE INDEX IF NOT EXISTS idx_subtasks_subtask_type ON subtasks(subtask_type);

UPDATE tasks AS t
SET
  requires_arrival_comment = COALESCE(tt.requires_arrival_comment, FALSE),
  requires_video_evidence = COALESCE(tt.requires_video_evidence, FALSE)
FROM task_templates AS tt
WHERE t.template_id = tt.template_id
  AND (
    t.requires_arrival_comment IS DISTINCT FROM COALESCE(tt.requires_arrival_comment, FALSE)
    OR t.requires_video_evidence IS DISTINCT FROM COALESCE(tt.requires_video_evidence, FALSE)
  );

UPDATE template_subtasks
SET subtask_type = 'standard'
WHERE subtask_type IS NULL OR subtask_type NOT IN ('standard', 'pre_form');

UPDATE subtasks AS s
SET subtask_type = COALESCE(ts.subtask_type, 'standard')
FROM template_subtasks AS ts
WHERE s.template_subtask_id = ts.template_subtask_id
  AND (
    s.subtask_type IS NULL
    OR s.subtask_type NOT IN ('standard', 'pre_form')
    OR s.subtask_type IS DISTINCT FROM COALESCE(ts.subtask_type, 'standard')
  );

UPDATE subtasks
SET subtask_type = 'standard'
WHERE subtask_type IS NULL OR subtask_type NOT IN ('standard', 'pre_form');

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_task_comments_comment_type'
  ) THEN
    ALTER TABLE task_comments DROP CONSTRAINT chk_task_comments_comment_type;
  END IF;

  ALTER TABLE task_comments
    ADD CONSTRAINT chk_task_comments_comment_type
    CHECK (
      comment_type IN (
        'general',
        'transition',
        'progress',
        'closure',
        'arrival_registration',
        'closure_evidence'
      )
    ) NOT VALID;
END
$$;

ALTER TABLE task_comments VALIDATE CONSTRAINT chk_task_comments_comment_type;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_template_subtasks_subtask_type'
  ) THEN
    ALTER TABLE template_subtasks DROP CONSTRAINT chk_template_subtasks_subtask_type;
  END IF;

  ALTER TABLE template_subtasks
    ADD CONSTRAINT chk_template_subtasks_subtask_type
    CHECK (subtask_type IN ('standard', 'pre_form')) NOT VALID;
END
$$;

ALTER TABLE template_subtasks VALIDATE CONSTRAINT chk_template_subtasks_subtask_type;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_subtasks_subtask_type'
  ) THEN
    ALTER TABLE subtasks DROP CONSTRAINT chk_subtasks_subtask_type;
  END IF;

  ALTER TABLE subtasks
    ADD CONSTRAINT chk_subtasks_subtask_type
    CHECK (subtask_type IN ('standard', 'pre_form')) NOT VALID;
END
$$;

ALTER TABLE subtasks VALIDATE CONSTRAINT chk_subtasks_subtask_type;

CREATE TABLE IF NOT EXISTS task_satisfaction_forms (
  form_id UUID PRIMARY KEY,
  task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
  token_hash VARCHAR(64) NOT NULL UNIQUE,
  created_by_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id),
  expires_at TIMESTAMPTZ NOT NULL,
  used_at TIMESTAMPTZ NULL,
  revoked_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_task_satisfaction_forms_task_id ON task_satisfaction_forms(task_id);
CREATE INDEX IF NOT EXISTS idx_task_satisfaction_forms_created_by_user_id ON task_satisfaction_forms(created_by_user_id);
CREATE INDEX IF NOT EXISTS idx_task_satisfaction_forms_expires_at ON task_satisfaction_forms(expires_at);

CREATE TABLE IF NOT EXISTS task_satisfaction_responses (
  response_id UUID PRIMARY KEY,
  form_id UUID NOT NULL UNIQUE REFERENCES task_satisfaction_forms(form_id) ON DELETE CASCADE,
  task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
  customer_name VARCHAR(255) NOT NULL,
  customer_company VARCHAR(255) NOT NULL,
  rating DOUBLE PRECISION NOT NULL,
  comment TEXT NULL,
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  submitter_ip_hash VARCHAR(64) NULL,
  submitter_user_agent VARCHAR(500) NULL,
  CONSTRAINT chk_task_satisfaction_rating_range CHECK (rating >= 1 AND rating <= 5)
);

CREATE INDEX IF NOT EXISTS idx_task_satisfaction_responses_task_id ON task_satisfaction_responses(task_id);

CREATE TABLE IF NOT EXISTS task_template_pre_forms (
  form_id UUID PRIMARY KEY,
  template_id UUID NOT NULL UNIQUE REFERENCES task_templates(template_id) ON DELETE CASCADE,
  title VARCHAR(255) NULL,
  instructions TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_task_template_pre_forms_template_id ON task_template_pre_forms(template_id);

CREATE TABLE IF NOT EXISTS task_template_pre_form_fields (
  field_id UUID PRIMARY KEY,
  form_id UUID NOT NULL REFERENCES task_template_pre_forms(form_id) ON DELETE CASCADE,
  label VARCHAR(255) NOT NULL,
  field_type VARCHAR(50) NOT NULL DEFAULT 'TEXT',
  is_required BOOLEAN NOT NULL DEFAULT TRUE,
  order_index INTEGER NOT NULL,
  placeholder VARCHAR(255) NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_task_template_pre_form_fields_type CHECK (field_type IN ('TEXT', 'NUMBER', 'TEXTAREA', 'DATE', 'TEL', 'FILE', 'CHECKBOX'))
);

CREATE INDEX IF NOT EXISTS idx_task_template_pre_form_fields_form_id ON task_template_pre_form_fields(form_id);

CREATE TABLE IF NOT EXISTS task_pre_form_instances (
  instance_id UUID PRIMARY KEY,
  task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
  template_pre_form_id UUID NULL REFERENCES task_template_pre_forms(form_id) ON DELETE SET NULL,
  token_hash VARCHAR(64) NOT NULL UNIQUE,
  expires_at TIMESTAMPTZ NOT NULL,
  submitted_at TIMESTAMPTZ NULL,
  revoked_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_task_pre_form_instances_task_id ON task_pre_form_instances(task_id);
CREATE INDEX IF NOT EXISTS idx_task_pre_form_instances_template_pre_form_id ON task_pre_form_instances(template_pre_form_id);
CREATE INDEX IF NOT EXISTS idx_task_pre_form_instances_expires_at ON task_pre_form_instances(expires_at);

CREATE TABLE IF NOT EXISTS task_pre_form_responses (
  response_id UUID PRIMARY KEY,
  instance_id UUID NOT NULL UNIQUE REFERENCES task_pre_form_instances(instance_id) ON DELETE CASCADE,
  task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  submitter_ip_hash VARCHAR(64) NULL
);

CREATE INDEX IF NOT EXISTS idx_task_pre_form_responses_task_id ON task_pre_form_responses(task_id);

CREATE TABLE IF NOT EXISTS task_pre_form_attachments (
  attachment_id UUID PRIMARY KEY,
  instance_id UUID NOT NULL REFERENCES task_pre_form_instances(instance_id) ON DELETE CASCADE,
  file_name VARCHAR(500) NOT NULL,
  file_url VARCHAR(1000) NOT NULL,
  mime_type VARCHAR(100) NULL,
  uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_task_pre_form_attachments_instance_id ON task_pre_form_attachments(instance_id);

CREATE TABLE IF NOT EXISTS task_pre_form_field_values (
  value_id UUID PRIMARY KEY,
  response_id UUID NOT NULL REFERENCES task_pre_form_responses(response_id) ON DELETE CASCADE,
  field_id UUID NOT NULL REFERENCES task_template_pre_form_fields(field_id) ON DELETE CASCADE,
  text_value TEXT NULL,
  file_attachment_id UUID NULL REFERENCES task_pre_form_attachments(attachment_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_task_pre_form_field_values_response_id ON task_pre_form_field_values(response_id);
CREATE INDEX IF NOT EXISTS idx_task_pre_form_field_values_field_id ON task_pre_form_field_values(field_id);
CREATE INDEX IF NOT EXISTS idx_task_pre_form_field_values_file_attachment_id ON task_pre_form_field_values(file_attachment_id);

COMMIT;
