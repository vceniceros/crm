-- Ticket closure and profile enhancements.
-- 1) Allow per-ticket closure video policy.
-- 2) Allow closing a ticket by marking a comment as solution.
-- 3) Store user avatar URL for self-service profile.

ALTER TABLE IF EXISTS tickets
  ADD COLUMN IF NOT EXISTS requires_video_evidence BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE IF EXISTS tickets
  ADD COLUMN IF NOT EXISTS solution_comment_id UUID NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_tickets_solution_comment'
  ) THEN
    ALTER TABLE tickets
      ADD CONSTRAINT fk_tickets_solution_comment
      FOREIGN KEY (solution_comment_id)
      REFERENCES ticket_comments(ticket_comment_id)
      ON DELETE SET NULL;
  END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_tickets_requires_video_evidence ON tickets(requires_video_evidence);
CREATE INDEX IF NOT EXISTS idx_tickets_solution_comment_id ON tickets(solution_comment_id);

ALTER TABLE IF EXISTS crm_users
  ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500) NULL;
