ALTER TABLE template_subtasks
    ADD COLUMN IF NOT EXISTS responsible_role_key VARCHAR(50),
    ADD COLUMN IF NOT EXISTS default_responsible_crm_user_id UUID REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS close_comment_required BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS next_assignment_policy VARCHAR(50) NOT NULL DEFAULT 'role_queue_auto';

CREATE INDEX IF NOT EXISTS idx_template_subtasks_responsible_role ON template_subtasks(responsible_role_key);

ALTER TABLE template_subtask_checklist_items
    ADD COLUMN IF NOT EXISTS item_type VARCHAR(50) NOT NULL DEFAULT 'checkbox';

ALTER TABLE subtasks
    ADD COLUMN IF NOT EXISTS responsible_role_key VARCHAR(50),
    ADD COLUMN IF NOT EXISTS default_responsible_crm_user_id UUID REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS close_comment_required BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS next_assignment_policy VARCHAR(50) NOT NULL DEFAULT 'role_queue_auto',
    ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'locked',
    ADD COLUMN IF NOT EXISTS closed_by_crm_user_id UUID REFERENCES crm_users(crm_user_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_subtasks_status ON subtasks(status);
CREATE INDEX IF NOT EXISTS idx_subtasks_responsible_role ON subtasks(responsible_role_key);

ALTER TABLE subtask_checklist_items
    ADD COLUMN IF NOT EXISTS template_checklist_item_id UUID REFERENCES template_subtask_checklist_items(template_checklist_item_id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS item_type VARCHAR(50) NOT NULL DEFAULT 'checkbox';

ALTER TABLE subtask_checklist_progress
    ADD COLUMN IF NOT EXISTS text_value TEXT;

CREATE TABLE IF NOT EXISTS task_comments (
    task_comment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    subtask_id UUID REFERENCES subtasks(subtask_id) ON DELETE CASCADE,
    author_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE RESTRICT,
    comment_type VARCHAR(50) NOT NULL DEFAULT 'transition',
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_task_comments_task ON task_comments(task_id, created_at);
CREATE INDEX IF NOT EXISTS idx_task_comments_subtask ON task_comments(subtask_id, created_at);

CREATE TABLE IF NOT EXISTS subtask_transitions (
    subtask_transition_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subtask_id UUID NOT NULL REFERENCES subtasks(subtask_id) ON DELETE CASCADE,
    task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    from_status VARCHAR(50) NOT NULL,
    to_status VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    performed_by_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE RESTRICT,
    task_comment_id UUID REFERENCES task_comments(task_comment_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_subtask_transitions_subtask ON subtask_transitions(subtask_id, created_at);
CREATE INDEX IF NOT EXISTS idx_subtask_transitions_task ON subtask_transitions(task_id, created_at);

CREATE TABLE IF NOT EXISTS task_audit_events (
    task_audit_event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    subtask_id UUID REFERENCES subtasks(subtask_id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    actor_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE RESTRICT,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_task_audit_events_task ON task_audit_events(task_id, created_at);
CREATE INDEX IF NOT EXISTS idx_task_audit_events_subtask ON task_audit_events(subtask_id, created_at);
CREATE INDEX IF NOT EXISTS idx_task_audit_events_type ON task_audit_events(event_type);