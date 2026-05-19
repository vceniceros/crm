-- Store optional geolocation evidence on ticket comments.

ALTER TABLE IF EXISTS ticket_comments
  ADD COLUMN IF NOT EXISTS location_id UUID NULL REFERENCES locations(location_id);

CREATE INDEX IF NOT EXISTS idx_ticket_comments_location ON ticket_comments(location_id);
