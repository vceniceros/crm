-- =============================================================================
-- 20260513_reassign_permissions_all_roles.sql
-- Habilita ticket.reassign para tecnico y deposito
-- =============================================================================

ALTER TABLE IF EXISTS crm_role_permissions
    ALTER COLUMN role_permission_id SET DEFAULT uuid_generate_v4();

INSERT INTO crm_role_permissions (role_permission_id, role_key, permission_code, is_granted)
VALUES
    (uuid_generate_v4(), 'tecnico', 'ticket.reassign', TRUE),
    (uuid_generate_v4(), 'deposito', 'ticket.reassign', TRUE)
ON CONFLICT (role_key, permission_code)
DO UPDATE SET is_granted = EXCLUDED.is_granted;
