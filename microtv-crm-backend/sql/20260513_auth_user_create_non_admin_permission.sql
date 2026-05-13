-- =============================================================================
-- 20260513_auth_user_create_non_admin_permission.sql
-- Habilita creacion de usuarios no-admin para ejecutivos via permisos
-- =============================================================================

-- Hardening para entornos donde la migracion 20260512 se registro sin defaults.
ALTER TABLE IF EXISTS crm_role_permissions
    ALTER COLUMN role_permission_id SET DEFAULT uuid_generate_v4();

INSERT INTO crm_role_permissions (role_permission_id, role_key, permission_code, is_granted) VALUES
    (uuid_generate_v4(), 'admin', 'auth_user.create_non_admin', TRUE),
    (uuid_generate_v4(), 'ejecutivo', 'auth_user.create_non_admin', TRUE)
ON CONFLICT (role_key, permission_code)
DO UPDATE SET is_granted = EXCLUDED.is_granted;
