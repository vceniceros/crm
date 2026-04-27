BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 20260306_0001

CREATE TABLE roles (
    role_id VARCHAR(36) NOT NULL, 
    role_name VARCHAR(100) NOT NULL, 
    description VARCHAR(255), 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (role_id)
);

CREATE UNIQUE INDEX ix_roles_role_name ON roles (role_name);

CREATE TABLE users (
    user_id VARCHAR(36) NOT NULL, 
    email VARCHAR(255) NOT NULL, 
    display_name VARCHAR(255) NOT NULL, 
    password_hash VARCHAR(512), 
    status VARCHAR(50) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (user_id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE memberships (
    membership_id VARCHAR(36) NOT NULL, 
    user_id VARCHAR(36) NOT NULL, 
    tenant_type VARCHAR(50) NOT NULL, 
    tenant_id VARCHAR(100) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (membership_id), 
    FOREIGN KEY(user_id) REFERENCES users (user_id)
);

CREATE INDEX ix_memberships_tenant_id ON memberships (tenant_id);

CREATE INDEX ix_memberships_user_id ON memberships (user_id);

INSERT INTO alembic_version (version_num) VALUES ('20260306_0001') RETURNING alembic_version.version_num;

-- Running upgrade 20260306_0001 -> 20260306_0002

CREATE TABLE role_assignments (
    assignment_id VARCHAR(36) NOT NULL, 
    membership_id VARCHAR(36) NOT NULL, 
    role_id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (assignment_id), 
    FOREIGN KEY(membership_id) REFERENCES memberships (membership_id), 
    FOREIGN KEY(role_id) REFERENCES roles (role_id)
);

CREATE INDEX ix_role_assignments_membership_id ON role_assignments (membership_id);

CREATE INDEX ix_role_assignments_role_id ON role_assignments (role_id);

UPDATE alembic_version SET version_num='20260306_0002' WHERE alembic_version.version_num = '20260306_0001';

-- Running upgrade 20260306_0002 -> 20260306_0003

CREATE TABLE login_tickets (
    ticket_id VARCHAR(36) NOT NULL, 
    user_id VARCHAR(36) NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    consumed_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (ticket_id), 
    FOREIGN KEY(user_id) REFERENCES users (user_id)
);

CREATE INDEX ix_login_tickets_expires_at ON login_tickets (expires_at);

CREATE INDEX ix_login_tickets_user_id ON login_tickets (user_id);

UPDATE alembic_version SET version_num='20260306_0003' WHERE alembic_version.version_num = '20260306_0002';

-- Running upgrade 20260306_0003 -> 20260308_0004

ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT 'false' NOT NULL;

ALTER TABLE users ADD COLUMN verification_token VARCHAR(36);

ALTER TABLE users ADD COLUMN verification_token_expires_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX ix_users_verification_token ON users (verification_token);

UPDATE alembic_version SET version_num='20260308_0004' WHERE alembic_version.version_num = '20260306_0003';

-- Running upgrade 20260308_0004 -> 20260308_0005

CREATE TABLE companies (
    company_id VARCHAR(20) NOT NULL, 
    company_name VARCHAR(255) NOT NULL, 
    logo_url VARCHAR(512), 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (company_id)
);

CREATE INDEX ix_companies_status ON companies (status);

ALTER TABLE users ADD COLUMN user_type VARCHAR(30) DEFAULT 'customer' NOT NULL;

UPDATE alembic_version SET version_num='20260308_0005' WHERE alembic_version.version_num = '20260308_0004';

-- Running upgrade 20260308_0005 -> 20260308_0006

INSERT INTO roles (role_id, role_name) VALUES ('5d0663da-3d00-456b-aad7-d96d31d98369', 'passenger_user') ON CONFLICT (role_name) DO NOTHING;

INSERT INTO roles (role_id, role_name) VALUES ('28296893-e42d-4d6a-b686-1cfb12fa4627', 'company_operator') ON CONFLICT (role_name) DO NOTHING;

INSERT INTO roles (role_id, role_name) VALUES ('c1a5ba57-8d6b-4f54-a2fa-0c54e730298d', 'company_admin') ON CONFLICT (role_name) DO NOTHING;

INSERT INTO roles (role_id, role_name) VALUES ('5e3ffe25-50b7-49f1-8e7c-e25be042aa0c', 'platform_admin') ON CONFLICT (role_name) DO NOTHING;

UPDATE alembic_version SET version_num='20260308_0006' WHERE alembic_version.version_num = '20260308_0005';

-- Running upgrade 20260308_0006 -> 20260309_0007

CREATE TABLE invitations (
    invitation_id VARCHAR(36) NOT NULL, 
    token VARCHAR(64) NOT NULL, 
    email VARCHAR(255) NOT NULL, 
    company_id VARCHAR(20) NOT NULL, 
    invited_by VARCHAR(36) NOT NULL, 
    status VARCHAR(20) DEFAULT 'pending' NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    accepted_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (invitation_id), 
    FOREIGN KEY(company_id) REFERENCES companies (company_id) ON DELETE CASCADE, 
    FOREIGN KEY(invited_by) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX ix_invitations_token ON invitations (token);

CREATE INDEX ix_invitations_email ON invitations (email);

UPDATE alembic_version SET version_num='20260309_0007' WHERE alembic_version.version_num = '20260308_0006';

COMMIT;

