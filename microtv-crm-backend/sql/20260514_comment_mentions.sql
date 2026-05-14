CREATE TABLE IF NOT EXISTS ticket_comment_mentions (
    ticket_comment_mention_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_comment_id UUID NOT NULL REFERENCES ticket_comments(ticket_comment_id) ON DELETE CASCADE,
    mentioned_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE CASCADE,
    created_by_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_ticket_comment_mentions_comment_user UNIQUE (ticket_comment_id, mentioned_crm_user_id)
);

CREATE INDEX IF NOT EXISTS ix_ticket_comment_mentions_ticket_comment_id
    ON ticket_comment_mentions(ticket_comment_id);

CREATE INDEX IF NOT EXISTS ix_ticket_comment_mentions_mentioned_crm_user_id
    ON ticket_comment_mentions(mentioned_crm_user_id);

CREATE INDEX IF NOT EXISTS ix_ticket_comment_mentions_created_by_crm_user_id
    ON ticket_comment_mentions(created_by_crm_user_id);

CREATE TABLE IF NOT EXISTS task_comment_mentions (
    task_comment_mention_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_comment_id UUID NOT NULL REFERENCES task_comments(task_comment_id) ON DELETE CASCADE,
    mentioned_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE CASCADE,
    created_by_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_task_comment_mentions_comment_user UNIQUE (task_comment_id, mentioned_crm_user_id)
);

CREATE INDEX IF NOT EXISTS ix_task_comment_mentions_task_comment_id
    ON task_comment_mentions(task_comment_id);

CREATE INDEX IF NOT EXISTS ix_task_comment_mentions_mentioned_crm_user_id
    ON task_comment_mentions(mentioned_crm_user_id);

CREATE INDEX IF NOT EXISTS ix_task_comment_mentions_created_by_crm_user_id
    ON task_comment_mentions(created_by_crm_user_id);
