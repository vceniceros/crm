-- Arrival comment requirement migration for ticket module.
-- Adds explicit arrival requirement and first-valid-comment registration fields.

ALTER TABLE IF EXISTS tickets
  ADD COLUMN IF NOT EXISTS requires_arrival_comment BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE IF EXISTS tickets
  ADD COLUMN IF NOT EXISTS arrival_registered_at TIMESTAMPTZ NULL;

ALTER TABLE IF EXISTS tickets
  ADD COLUMN IF NOT EXISTS arrival_comment_id UUID NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_tickets_arrival_comment'
  ) THEN
    ALTER TABLE tickets
      ADD CONSTRAINT fk_tickets_arrival_comment
      FOREIGN KEY (arrival_comment_id)
      REFERENCES ticket_comments(ticket_comment_id)
      ON DELETE SET NULL;
  END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_tickets_arrival_comment_id ON tickets(arrival_comment_id);
CREATE INDEX IF NOT EXISTS idx_tickets_requires_arrival_comment ON tickets(requires_arrival_comment);
