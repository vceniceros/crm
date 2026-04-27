ALTER TABLE task_attachments
    ADD COLUMN IF NOT EXISTS task_comment_id UUID REFERENCES task_comments(task_comment_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_task_attachments_comment ON task_attachments(task_comment_id);