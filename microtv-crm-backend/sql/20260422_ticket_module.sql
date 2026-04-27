-- Ticket module schema extension
-- Compatible with PostgreSQL schema used by microtv-crm-backend.

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id UUID PRIMARY KEY,
    ticket_number VARCHAR(30) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    client_id UUID NOT NULL REFERENCES clients(client_id),
    location_id UUID NOT NULL REFERENCES locations(location_id),
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
    priority VARCHAR(30) NOT NULL DEFAULT 'MEDIUM',
    assigned_role_id UUID NULL REFERENCES crm_roles(crm_role_id),
    assigned_user_id UUID NULL REFERENCES crm_users(crm_user_id),
    created_by_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id),
    resolved_by_crm_user_id UUID NULL REFERENCES crm_users(crm_user_id),
    resolved_at TIMESTAMPTZ NULL,
    closed_by_crm_user_id UUID NULL REFERENCES crm_users(crm_user_id),
    closed_at TIMESTAMPTZ NULL,
    requires_arrival_comment BOOLEAN NOT NULL DEFAULT FALSE,
    arrival_registered_at TIMESTAMPTZ NULL,
    arrival_comment_id UUID NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE TABLE IF NOT EXISTS ticket_comments (
    ticket_comment_id UUID PRIMARY KEY,
    ticket_id UUID NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    author_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id),
    comment_type VARCHAR(30) NOT NULL DEFAULT 'general',
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ticket_attachments (
    attachment_id UUID PRIMARY KEY,
    ticket_id UUID NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    ticket_comment_id UUID NULL REFERENCES ticket_comments(ticket_comment_id) ON DELETE SET NULL,
    file_name VARCHAR(500) NOT NULL,
    file_url VARCHAR(1000) NOT NULL,
    file_size_bytes INTEGER NULL,
    mime_type VARCHAR(100) NULL,
    attachment_type VARCHAR(50) NOT NULL DEFAULT 'PHOTO',
    uploaded_by_crm_user_id UUID NULL REFERENCES crm_users(crm_user_id),
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ticket_status_transitions (
    ticket_status_transition_id UUID PRIMARY KEY,
    ticket_id UUID NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    from_status VARCHAR(30) NOT NULL,
    to_status VARCHAR(30) NOT NULL,
    action VARCHAR(50) NOT NULL,
    performed_by_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id),
    ticket_comment_id UUID NULL REFERENCES ticket_comments(ticket_comment_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ticket_assignment_history (
    ticket_assignment_id UUID PRIMARY KEY,
    ticket_id UUID NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    previous_role_id UUID NULL REFERENCES crm_roles(crm_role_id),
    previous_user_id UUID NULL REFERENCES crm_users(crm_user_id),
    assigned_role_id UUID NULL REFERENCES crm_roles(crm_role_id),
    assigned_user_id UUID NULL REFERENCES crm_users(crm_user_id),
    assigned_by_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id),
    notes TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ticket_audit_events (
    ticket_audit_event_id UUID PRIMARY KEY,
    ticket_id UUID NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    actor_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id),
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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

CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_client ON tickets(client_id);
CREATE INDEX IF NOT EXISTS idx_tickets_location ON tickets(location_id);
CREATE INDEX IF NOT EXISTS idx_tickets_assigned_role ON tickets(assigned_role_id);
CREATE INDEX IF NOT EXISTS idx_tickets_assigned_user ON tickets(assigned_user_id);
CREATE INDEX IF NOT EXISTS idx_tickets_created_by ON tickets(created_by_crm_user_id);
CREATE INDEX IF NOT EXISTS idx_tickets_requires_arrival_comment ON tickets(requires_arrival_comment);
CREATE INDEX IF NOT EXISTS idx_tickets_arrival_comment_id ON tickets(arrival_comment_id);
CREATE INDEX IF NOT EXISTS idx_ticket_comments_ticket ON ticket_comments(ticket_id);
CREATE INDEX IF NOT EXISTS idx_ticket_attachments_ticket ON ticket_attachments(ticket_id);
CREATE INDEX IF NOT EXISTS idx_ticket_attachments_comment ON ticket_attachments(ticket_comment_id);
CREATE INDEX IF NOT EXISTS idx_ticket_status_transitions_ticket ON ticket_status_transitions(ticket_id);
CREATE INDEX IF NOT EXISTS idx_ticket_assignment_history_ticket ON ticket_assignment_history(ticket_id);
CREATE INDEX IF NOT EXISTS idx_ticket_audit_events_ticket ON ticket_audit_events(ticket_id);
