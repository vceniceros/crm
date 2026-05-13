-- =============================================================================
-- 20260513_auth_user_create_non_admin_permission.sql
-- Habilita creacion de usuarios no-admin para ejecutivos via permisos
-- =============================================================================

INSERT INTO crm_role_permissions (role_key, permission_code, is_granted) VALUES
    ('admin', 'auth_user.create_non_admin', TRUE),
    ('ejecutivo', 'auth_user.create_non_admin', TRUE)
ON CONFLICT (role_key, permission_code)
DO UPDATE SET is_granted = EXCLUDED.is_granted;
