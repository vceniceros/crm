-- =====================================================
-- MicroTV CRM - Esquema de Base de Datos Relacional
-- Versión: 4.0 (Integración con auth.microtv.ar - Contexto auth persistido)
-- Fecha: Abril 2026
-- Normalización: BCNF donde razonable, 3NF mínimo
-- =====================================================
--
-- SEPARACIÓN DE RESPONSABILIDADES:
-- ┌─────────────────────────────────────────────────────────────┐
-- │ auth.microtv.ar (Sistema externo, base de datos separada)  │
-- │ - Autenticación (login, logout)                             │
-- │ - Contraseñas (Argon2)                                      │
-- │ - Sesiones JWT (access_token, refresh_token)                │
-- │ - Multi-tenancy (memberships, contextos)                    │
-- │ - Roles de identidad                                        │
-- └─────────────────────────────────────────────────────────────┘
--
-- ┌─────────────────────────────────────────────────────────────┐
-- │ CRM (Este esquema)                                          │
-- │ - Perfil operativo de usuarios                              │
-- │ - Roles funcionales del CRM (crm_roles)                     │
-- │ - Snapshot contextual de auth (últimos claims JWT)          │
-- │ - Datos de negocio (clientes, tasks, tickets, inventario)  │
-- │ - Trazabilidad operativa                                    │
-- └─────────────────────────────────────────────────────────────┘
--
-- INTEGRACIÓN:
-- - auth_user_id es una REFERENCIA LÓGICA (NO foreign key física)
-- - El contexto auth (membership, tenant, roles) se persiste como SNAPSHOT/CACHE
-- - La validación proviene del JWT (claims 'sub' y 'active_membership')
-- - El backend del CRM es responsable de:
--   1. Validar JWT contra auth.microtv.ar
--   2. Extraer claims (sub, email, display_name, active_membership)
--   3. Sincronizar/upsert crm_users automáticamente con contexto auth
-- - Los roles de auth NO reemplazan crm_roles (roles funcionales del CRM)
-- - NO hay password_hash, user_sessions, ni lógica de autenticación duplicada
--
-- =====================================================

-- Extensiones necesarias (PostgreSQL)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- SECCIÓN 1: USUARIOS Y ROLES LOCALES DEL CRM
-- Integración con auth.microtv.ar
-- =====================================================

-- Tabla: crm_users
-- Usuarios del CRM (perfil operativo local, NO gestiona autenticación)
CREATE TABLE crm_users (
    -- Identidad local del CRM
    crm_user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Referencia lógica externa a auth.microtv.ar (claim 'sub' del JWT)
    -- NO es foreign key física (sistemas desacoplados, bases de datos separadas)
    auth_user_id VARCHAR(36) NOT NULL UNIQUE,
    
    -- Cache denormalizado de auth: datos básicos del usuario
    -- (non-authoritative, actualizable desde JWT)
    email VARCHAR(255),
    display_name VARCHAR(255),
    cached_at TIMESTAMPTZ,
    
    -- Snapshot contextual de auth: último contexto conocido (claim 'active_membership' del JWT)
    -- NO reemplaza crm_roles. Sirve para trazabilidad, debugging, UI y lógica contextual.
    last_auth_membership_id VARCHAR(36),
    last_auth_tenant_type VARCHAR(50),
    last_auth_tenant_id VARCHAR(36),
    last_auth_roles_json JSONB,
    last_auth_context_synced_at TIMESTAMPTZ,
    
    -- Datos operativos locales del CRM
    phone VARCHAR(50),
    initials VARCHAR(10), -- Para avatares (ej: "SM", "MD", "LF")
    is_active_in_crm BOOLEAN NOT NULL DEFAULT TRUE, -- Actividad local del CRM
    last_seen_in_crm_at TIMESTAMPTZ,
    
    -- Auditoría
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ,
    
    -- Constraint simbólica: nunca almacenar password_hash aquí
    CONSTRAINT chk_no_passwords CHECK (TRUE)
);

CREATE INDEX idx_crm_users_auth_user_id ON crm_users(auth_user_id);
CREATE INDEX idx_crm_users_email ON crm_users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_crm_users_active ON crm_users(is_active_in_crm) WHERE deleted_at IS NULL;
CREATE INDEX idx_crm_users_auth_tenant ON crm_users(last_auth_tenant_type, last_auth_tenant_id) WHERE deleted_at IS NULL;

COMMENT ON TABLE crm_users IS 
'Usuarios del CRM con perfil operativo local. 
auth_user_id es REFERENCIA LÓGICA a auth.microtv.ar (NO foreign key física). 
Persiste snapshot del contexto auth (membership/tenant/roles) como cache. 
La sincronización ocurre en el backend al validar JWT. 
NO contiene credenciales ni gestiona autenticación.';

COMMENT ON COLUMN crm_users.auth_user_id IS 
'Identificador externo del usuario en auth.microtv.ar (claim sub del JWT). 
REFERENCIA LÓGICA, NO foreign key física (sistemas desacoplados). 
El backend valida JWT y sincroniza este usuario automáticamente.';

COMMENT ON COLUMN crm_users.email IS 
'Cache de auth.users.email. NO autoritativo. 
Actualizar desde JWT claims en cada autenticación.';

COMMENT ON COLUMN crm_users.display_name IS 
'Cache de auth.users.display_name. NO autoritativo. 
Actualizar desde JWT claims.';

COMMENT ON COLUMN crm_users.cached_at IS 
'Timestamp de última sincronización del cache de datos básicos desde JWT.';

COMMENT ON COLUMN crm_users.last_auth_membership_id IS 
'ID de la membership activa en auth.microtv.ar (claim active_membership.membership_id). 
SNAPSHOT/CACHE contextual, NO autoritativo. 
Actualizado por el backend del CRM al validar JWT. 
NO es foreign key física.';

COMMENT ON COLUMN crm_users.last_auth_tenant_type IS 
'Tipo de tenant en auth (claim active_membership.tenant_type: company, etc.). 
SNAPSHOT/CACHE contextual, NO autoritativo. 
Sirve para trazabilidad y lógica contextual (ej: mostrar nombre de empresa en UI).';

COMMENT ON COLUMN crm_users.last_auth_tenant_id IS 
'ID del tenant en auth (claim active_membership.tenant_id). 
SNAPSHOT/CACHE contextual, NO autoritativo. 
NO es foreign key física.';

COMMENT ON COLUMN crm_users.last_auth_roles_json IS 
'Array JSON de roles del usuario en auth para el tenant activo 
(claim active_membership.roles: ["admin", "viewer"], etc.). 
SNAPSHOT/CACHE contextual, NO autoritativo. 
NO reemplaza crm_roles (roles funcionales locales del CRM). 
Sirve para trazabilidad, debugging, UI y lógica contextual de negocio.';

COMMENT ON COLUMN crm_users.last_auth_context_synced_at IS 
'Timestamp de última sincronización del contexto auth (membership/tenant/roles) desde JWT. 
Sirve para detectar datos desactualizados.';

COMMENT ON COLUMN crm_users.is_active_in_crm IS 
'Actividad LOCAL del CRM (suspensión operativa), 
independiente de auth.users.status.';

-- Tabla: crm_roles
-- Roles funcionales del CRM (capacidades operativas)
CREATE TABLE crm_roles (
    crm_role_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_key VARCHAR(50) NOT NULL UNIQUE,
    role_label VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_crm_roles_key ON crm_roles(role_key) WHERE is_active = TRUE;

COMMENT ON TABLE crm_roles IS 
'Roles FUNCIONALES del CRM (capacidades operativas dentro del sistema). 
NO son roles de identidad (esos vienen de auth.microtv.ar via JWT claims). 
NO son reemplazados por last_auth_roles_json (que es solo snapshot contextual).';

COMMENT ON COLUMN crm_roles.role_key IS 
'Identificador único del rol funcional del CRM: 
admin_crm, tecnico_campo, encargado_deposito, dispatcher, etc.';

-- Tabla: crm_user_roles
-- Asignación de roles funcionales a usuarios del CRM
CREATE TABLE crm_user_roles (
    crm_user_role_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE CASCADE,
    crm_role_id UUID NOT NULL REFERENCES crm_roles(crm_role_id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    assigned_by_crm_user_id UUID REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    
    UNIQUE(crm_user_id, crm_role_id)
);

CREATE INDEX idx_crm_user_roles_user ON crm_user_roles(crm_user_id);
CREATE INDEX idx_crm_user_roles_role ON crm_user_roles(crm_role_id);

COMMENT ON TABLE crm_user_roles IS 
'Asignación de roles funcionales del CRM a usuarios (M2M). 
Representa capacidades operativas, NO roles de autenticación. 
Independiente de last_auth_roles_json (que es solo snapshot de auth).';

-- =====================================================
-- SECCIÓN 2: CLIENTES Y GEOGRAFÍA
-- =====================================================

-- Tabla: clients
-- Clientes del CRM (empresas/personas a las que se brinda servicio)
CREATE TABLE clients (
    client_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_name VARCHAR(255) NOT NULL,
    tax_id VARCHAR(50) NOT NULL UNIQUE, -- CUIT en Argentina
    email VARCHAR(255),
    phone VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ,
    
    CONSTRAINT chk_client_email_format 
        CHECK (email IS NULL OR email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

CREATE INDEX idx_clients_tax_id ON clients(tax_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_clients_active ON clients(is_active) WHERE deleted_at IS NULL;

COMMENT ON TABLE clients IS 
'Clientes del CRM (NO confundir con auth.companies que son organizaciones operadoras)';

COMMENT ON COLUMN clients.tax_id IS 'CUIT o identificación fiscal única';

-- Tabla: locations
-- Ubicaciones geográficas normalizadas
CREATE TABLE locations (
    location_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    address_label VARCHAR(500),
    formatted_address TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_latitude CHECK (latitude BETWEEN -90 AND 90),
    CONSTRAINT chk_longitude CHECK (longitude BETWEEN -180 AND 180)
);

CREATE INDEX idx_locations_coords ON locations(latitude, longitude);

COMMENT ON TABLE locations IS 
'Ubicaciones geográficas normalizadas (no necesariamente pertenecen a un cliente)';

-- Tabla: client_locations
-- Relación many-to-many: un cliente puede tener múltiples sedes/oficinas
CREATE TABLE client_locations (
    client_location_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    location_id UUID NOT NULL REFERENCES locations(location_id) ON DELETE CASCADE,
    location_label VARCHAR(255), -- Ej: "Casa Central", "Sucursal Norte"
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(client_id, location_id)
);

CREATE INDEX idx_client_locations_client ON client_locations(client_id);
CREATE INDEX idx_client_locations_location ON client_locations(location_id);

-- Índice único parcial: solo UNA ubicación primaria por cliente
CREATE UNIQUE INDEX idx_client_locations_primary_unique 
    ON client_locations(client_id) 
    WHERE is_primary = TRUE;

COMMENT ON TABLE client_locations IS 
'Sedes/oficinas del cliente (many-to-many). 
Constraint: máximo una ubicación primaria por cliente.';

-- =====================================================
-- SECCIÓN 3: INVENTARIO Y PRODUCTOS
-- =====================================================

-- Tabla: warehouses
-- Almacenes/depósitos físicos
CREATE TABLE warehouses (
    warehouse_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    warehouse_name VARCHAR(255) NOT NULL UNIQUE,
    address TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_warehouses_active ON warehouses(is_active);

COMMENT ON TABLE warehouses IS 
'Almacenes/depósitos físicos donde se gestiona inventario';

-- Tabla: inventory_categories
-- Categorías de productos de inventario
CREATE TABLE inventory_categories (
    category_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    parent_category_id UUID REFERENCES inventory_categories(category_id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_inventory_categories_parent ON inventory_categories(parent_category_id);

COMMENT ON TABLE inventory_categories IS 
'Categorías de productos (puede ser jerárquico)';

-- Tabla: inventory_products
-- Catálogo de productos (definición, NO stock)
CREATE TABLE inventory_products (
    product_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_id UUID REFERENCES inventory_categories(category_id) ON DELETE SET NULL,
    product_name VARCHAR(255) NOT NULL,
    product_code VARCHAR(100) UNIQUE, -- SKU o código interno
    barcode VARCHAR(255),
    description TEXT,
    unit_of_measure VARCHAR(50), -- 'unidad', 'metro', 'kg', etc.
    image_url VARCHAR(500),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_inventory_products_category ON inventory_products(category_id);
CREATE INDEX idx_inventory_products_code ON inventory_products(product_code) WHERE deleted_at IS NULL;
CREATE INDEX idx_inventory_products_barcode ON inventory_products(barcode) WHERE deleted_at IS NULL;

COMMENT ON TABLE inventory_products IS 
'Catálogo de productos (definición sin stock)';

-- Tabla: inventory_stock
-- Stock actual por producto y almacén
CREATE TABLE inventory_stock (
    stock_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES inventory_products(product_id) ON DELETE CASCADE,
    warehouse_id UUID NOT NULL REFERENCES warehouses(warehouse_id) ON DELETE CASCADE,
    quantity_available DECIMAL(12, 3) NOT NULL DEFAULT 0,
    quantity_reserved DECIMAL(12, 3) NOT NULL DEFAULT 0,
    minimum_stock DECIMAL(12, 3),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_quantity_available CHECK (quantity_available >= 0),
    CONSTRAINT chk_quantity_reserved CHECK (quantity_reserved >= 0),
    
    UNIQUE(product_id, warehouse_id)
);

CREATE INDEX idx_inventory_stock_product ON inventory_stock(product_id);
CREATE INDEX idx_inventory_stock_warehouse ON inventory_stock(warehouse_id);

COMMENT ON TABLE inventory_stock IS 
'Stock actual por producto y almacén. 
warehouse_id es NOT NULL (al menos un depósito debe existir).';

-- Tabla: inventory_movements
-- Trazabilidad de movimientos de stock
CREATE TABLE inventory_movements (
    movement_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES inventory_products(product_id) ON DELETE CASCADE,
    warehouse_id UUID NOT NULL REFERENCES warehouses(warehouse_id) ON DELETE CASCADE,
    movement_type VARCHAR(50) NOT NULL, -- 'IN', 'OUT', 'ADJUSTMENT', 'CONSUMPTION', 'RETURN'
    quantity DECIMAL(12, 3) NOT NULL,
    
    -- Referencia polimórfica débil (MVP simplificado)
    -- Ejemplos: 'TICKET', 'TASK', 'MANUAL_ADJUSTMENT'
    -- El backend es responsable de mantener consistencia
    reference_entity_type VARCHAR(50),
    reference_entity_id UUID,
    
    notes TEXT,
    performed_by_crm_user_id UUID REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    performed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_movement_type 
        CHECK (movement_type IN ('IN', 'OUT', 'ADJUSTMENT', 'CONSUMPTION', 'RETURN'))
);

CREATE INDEX idx_inventory_movements_product ON inventory_movements(product_id);
CREATE INDEX idx_inventory_movements_warehouse ON inventory_movements(warehouse_id);
CREATE INDEX idx_inventory_movements_type ON inventory_movements(movement_type);
CREATE INDEX idx_inventory_movements_reference ON inventory_movements(reference_entity_type, reference_entity_id);
CREATE INDEX idx_inventory_movements_date ON inventory_movements(performed_at);

COMMENT ON TABLE inventory_movements IS 
'Historial de movimientos de stock para trazabilidad completa. 
Usa referencia polimórfica débil (reference_entity_type/id) para MVP. 
El backend mantiene consistencia entre movements y entidades referenciadas.';

COMMENT ON COLUMN inventory_movements.reference_entity_type IS 
'Tipo de entidad que causó el movimiento: TICKET, TASK, MANUAL_ADJUSTMENT, etc. 
Polimorfismo débil: el backend valida consistencia.';

-- Tabla: stock_devices
-- Dispositivos/equipos que el cliente tiene (ej: DVR, cámaras)
CREATE TABLE stock_devices (
    device_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_type VARCHAR(100) NOT NULL,
    brand VARCHAR(100),
    model VARCHAR(100),
    serial_number VARCHAR(255) UNIQUE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stock_devices_serial ON stock_devices(serial_number);

COMMENT ON TABLE stock_devices IS 
'Catálogo de dispositivos/equipos (DVR, cámaras, etc.) que pueden ser afectados en tickets';

-- Tabla: client_devices
-- Relación many-to-many: qué dispositivos tiene cada cliente
CREATE TABLE client_devices (
    client_device_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    device_id UUID NOT NULL REFERENCES stock_devices(device_id) ON DELETE CASCADE,
    installation_date DATE,
    location_id UUID REFERENCES locations(location_id) ON DELETE SET NULL,
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(client_id, device_id)
);

CREATE INDEX idx_client_devices_client ON client_devices(client_id);
CREATE INDEX idx_client_devices_device ON client_devices(device_id);

COMMENT ON TABLE client_devices IS 
'Dispositivos instalados en cada cliente';

-- =====================================================
-- SECCIÓN 4: TEMPLATES DE TAREAS
-- =====================================================

-- Tabla: task_templates
-- Plantillas reutilizables de tareas
CREATE TABLE task_templates (
    template_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_name VARCHAR(255) NOT NULL,
    description TEXT,
    estimated_duration_hours DECIMAL(6, 2),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by_crm_user_id UUID REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_task_templates_active ON task_templates(is_active);

COMMENT ON TABLE task_templates IS 
'Plantillas reutilizables de tareas (ej: Instalación estándar DVR)';

-- Tabla: template_subtasks
-- Subtareas predefinidas en un template
CREATE TABLE template_subtasks (
    template_subtask_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID NOT NULL REFERENCES task_templates(template_id) ON DELETE CASCADE,
    parent_template_subtask_id UUID REFERENCES template_subtasks(template_subtask_id) ON DELETE CASCADE,
    subtask_title VARCHAR(255) NOT NULL,
    subtask_description TEXT,
    order_index INT NOT NULL,
    estimated_duration_minutes INT,
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_template_order_index CHECK (order_index >= 0),
    UNIQUE(template_id, order_index)
);

CREATE INDEX idx_template_subtasks_template ON template_subtasks(template_id, order_index);
CREATE INDEX idx_template_subtasks_parent ON template_subtasks(parent_template_subtask_id);

COMMENT ON TABLE template_subtasks IS 
'Subtareas predefinidas en templates (jerárquicas con orden secuencial). 
Constraint: order_index único por template.';

-- Tabla: template_subtask_checklist_items
-- Items de checklist predefinidos para subtareas de template
CREATE TABLE template_subtask_checklist_items (
    template_checklist_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_subtask_id UUID NOT NULL REFERENCES template_subtasks(template_subtask_id) ON DELETE CASCADE,
    item_label VARCHAR(500) NOT NULL,
    item_order INT NOT NULL,
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_template_checklist_item_order CHECK (item_order >= 0),
    UNIQUE(template_subtask_id, item_order)
);

CREATE INDEX idx_template_subtask_checklist_items_subtask 
    ON template_subtask_checklist_items(template_subtask_id, item_order);

COMMENT ON TABLE template_subtask_checklist_items IS 
'Items de checklist predefinidos en templates. 
El backend los instancia al crear una task desde template.';

-- Tabla: template_materials
-- Materiales/productos requeridos por un template
CREATE TABLE template_materials (
    template_material_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID NOT NULL REFERENCES task_templates(template_id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES inventory_products(product_id) ON DELETE CASCADE,
    quantity_required DECIMAL(12, 3) NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(template_id, product_id)
);

CREATE INDEX idx_template_materials_template ON template_materials(template_id);
CREATE INDEX idx_template_materials_product ON template_materials(product_id);

COMMENT ON TABLE template_materials IS 
'Materiales requeridos por un template de tarea';

-- =====================================================
-- SECCIÓN 5: TAREAS (TASKS)
-- =====================================================

-- Tabla: tasks
-- Tareas (épicas/trabajos grandes)
CREATE TABLE tasks (
    task_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_title VARCHAR(255) NOT NULL,
    task_description TEXT,
    client_id UUID NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    location_id UUID REFERENCES locations(location_id) ON DELETE SET NULL,
    template_id UUID REFERENCES task_templates(template_id) ON DELETE SET NULL,
    current_assigned_crm_user_id UUID REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    priority VARCHAR(50) NOT NULL DEFAULT 'MEDIA',
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    is_finalized BOOLEAN NOT NULL DEFAULT FALSE,
    finalized_at TIMESTAMPTZ,
    finalized_by_crm_user_id UUID REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    
    -- Creador histórico: NOT NULL + ON DELETE RESTRICT (preservar trazabilidad)
    created_by_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ,
    
    CONSTRAINT chk_task_priority CHECK (priority IN ('BAJA', 'MEDIA', 'ALTA', 'CRITICA')),
    CONSTRAINT chk_task_status CHECK (status IN ('PENDING', 'IN_PROGRESS', 'BLOCKED', 'COMPLETED'))
);

CREATE INDEX idx_tasks_client ON tasks(client_id);
CREATE INDEX idx_tasks_location ON tasks(location_id);
CREATE INDEX idx_tasks_assigned_user ON tasks(current_assigned_crm_user_id);
CREATE INDEX idx_tasks_status ON tasks(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
CREATE INDEX idx_tasks_created_by ON tasks(created_by_crm_user_id);

COMMENT ON TABLE tasks IS 
'Tareas (trabajos grandes divididos en subtareas)';

-- Tabla: task_material_assignments
-- Materiales asignados/consumidos en una task
CREATE TABLE task_material_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES inventory_products(product_id) ON DELETE CASCADE,
    quantity_assigned DECIMAL(12, 3) NOT NULL,
    quantity_consumed DECIMAL(12, 3) NOT NULL DEFAULT 0,
    
    -- Quién asignó los materiales
    assigned_by_crm_user_id UUID REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    notes TEXT,
    
    CONSTRAINT chk_task_material_quantity_assigned CHECK (quantity_assigned > 0),
    CONSTRAINT chk_task_material_quantity_consumed CHECK (quantity_consumed >= 0),
    CONSTRAINT chk_task_material_consumed_lte_assigned CHECK (quantity_consumed <= quantity_assigned),
    
    UNIQUE(task_id, product_id)
);

CREATE INDEX idx_task_material_assignments_task ON task_material_assignments(task_id);
CREATE INDEX idx_task_material_assignments_product ON task_material_assignments(product_id);

COMMENT ON TABLE task_material_assignments IS 
'Materiales asignados y consumidos en tasks. 
NO usa el flujo de requests/approvals (eso es para tickets). 
Tasks son épicas planificadas: los materiales se asignan por adelantado.';

-- Tabla: subtasks
-- Subtareas de una tarea (instancias ejecutables)
CREATE TABLE subtasks (
    subtask_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    parent_subtask_id UUID REFERENCES subtasks(subtask_id) ON DELETE CASCADE,
    template_subtask_id UUID REFERENCES template_subtasks(template_subtask_id) ON DELETE SET NULL,
    subtask_title VARCHAR(255) NOT NULL,
    subtask_description TEXT,
    order_index INT NOT NULL,
    current_assigned_crm_user_id UUID REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    completion_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_subtask_order_index CHECK (order_index >= 0),
    CONSTRAINT chk_subtask_completion_notes 
        CHECK (is_completed = FALSE OR completion_notes IS NOT NULL),
    UNIQUE(task_id, order_index)
);

CREATE INDEX idx_subtasks_task ON subtasks(task_id, order_index);
CREATE INDEX idx_subtasks_parent ON subtasks(parent_subtask_id);
CREATE INDEX idx_subtasks_assigned_user ON subtasks(current_assigned_crm_user_id);
CREATE INDEX idx_subtasks_completed ON subtasks(is_completed);

COMMENT ON TABLE subtasks IS 
'Subtareas de una tarea (instancias ejecutables con secuencia). 
Constraints: 
- order_index único por task
- completion_notes obligatorio cuando is_completed = TRUE';

-- Tabla: subtask_checklist_items
-- Items/checks dentro de una subtarea
CREATE TABLE subtask_checklist_items (
    checklist_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subtask_id UUID NOT NULL REFERENCES subtasks(subtask_id) ON DELETE CASCADE,
    item_label VARCHAR(500) NOT NULL,
    item_order INT NOT NULL,
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_checklist_item_order CHECK (item_order >= 0),
    UNIQUE(subtask_id, item_order)
);

CREATE INDEX idx_subtask_checklist_items_subtask ON subtask_checklist_items(subtask_id, item_order);

COMMENT ON TABLE subtask_checklist_items IS 
'Items/checks dentro de una subtarea (ej: verificar voltaje, instalar bracket). 
Constraint: item_order único por subtask.';

-- Tabla: subtask_checklist_progress
-- Progreso de checklist (qué items están completados)
CREATE TABLE subtask_checklist_progress (
    progress_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    checklist_item_id UUID NOT NULL REFERENCES subtask_checklist_items(checklist_item_id) ON DELETE CASCADE,
    is_checked BOOLEAN NOT NULL DEFAULT FALSE,
    checked_at TIMESTAMPTZ,
    checked_by_crm_user_id UUID REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    
    UNIQUE(checklist_item_id)
);

CREATE INDEX idx_subtask_checklist_progress_item ON subtask_checklist_progress(checklist_item_id);

COMMENT ON TABLE subtask_checklist_progress IS 
'Progreso de checklist (qué items están marcados)';

-- Tabla: subtask_assignments
-- Historial de asignaciones de subtarea
CREATE TABLE subtask_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subtask_id UUID NOT NULL REFERENCES subtasks(subtask_id) ON DELETE CASCADE,
    
    -- Asignado histórico: NOT NULL + ON DELETE RESTRICT
    assigned_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE RESTRICT,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    assigned_by_crm_user_id UUID REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    unassigned_at TIMESTAMPTZ,
    notes TEXT
);

CREATE INDEX idx_subtask_assignments_subtask ON subtask_assignments(subtask_id, assigned_at DESC);
CREATE INDEX idx_subtask_assignments_user ON subtask_assignments(assigned_crm_user_id);

COMMENT ON TABLE subtask_assignments IS 
'Historial de asignaciones de subtareas (trazabilidad de cambios de manos). 
assigned_crm_user_id es NOT NULL + ON DELETE RESTRICT (preservar historial).';

-- Tabla: task_attachments
-- Adjuntos multimedia de tareas/subtareas
CREATE TABLE task_attachments (
    attachment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    subtask_id UUID REFERENCES subtasks(subtask_id) ON DELETE CASCADE,
    file_name VARCHAR(500) NOT NULL,
    file_url VARCHAR(1000) NOT NULL,
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),
    attachment_type VARCHAR(50) NOT NULL, -- 'PHOTO', 'VIDEO', 'DOCUMENT'
    uploaded_by_crm_user_id UUID REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_attachment_type CHECK (attachment_type IN ('PHOTO', 'VIDEO', 'DOCUMENT'))
);

CREATE INDEX idx_task_attachments_task ON task_attachments(task_id);
CREATE INDEX idx_task_attachments_subtask ON task_attachments(subtask_id);
CREATE INDEX idx_task_attachments_uploaded_at ON task_attachments(uploaded_at);

COMMENT ON TABLE task_attachments IS 
'Adjuntos multimedia (fotos, videos) de tareas/subtareas';

-- =====================================================
-- SECCIÓN 6: TICKETS
-- =====================================================

-- Tabla: ticket_categories
-- Categorías de tickets
CREATE TABLE ticket_categories (
    category_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE ticket_categories IS 
'Categorías de tickets (ej: Soporte técnico, Mantenimiento)';

-- Tabla: ticket_statuses
-- Estados del ciclo de vida del ticket
CREATE TABLE ticket_statuses (
    status_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status_key VARCHAR(50) NOT NULL UNIQUE,
    status_label VARCHAR(100) NOT NULL,
    status_order INT NOT NULL,
    is_final BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_status_order CHECK (status_order >= 0)
);

COMMENT ON TABLE ticket_statuses IS 
'Estados del ciclo de vida del ticket (open, in_progress, resolved, closed)';

-- Tabla: ticket_priorities
-- Prioridades de tickets
CREATE TABLE ticket_priorities (
    priority_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    priority_key VARCHAR(50) NOT NULL UNIQUE,
    priority_label VARCHAR(100) NOT NULL,
    priority_level INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_priority_level CHECK (priority_level >= 0)
);

COMMENT ON TABLE ticket_priorities IS 
'Prioridades de tickets (baja, media, alta, crítica)';

-- Tabla: tickets
-- Tickets (incidencias/problemas)
CREATE TABLE tickets (
    ticket_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_title VARCHAR(255) NOT NULL,
    ticket_description TEXT,
    client_id UUID NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    location_id UUID REFERENCES locations(location_id) ON DELETE SET NULL,
    category_id UUID REFERENCES ticket_categories(category_id) ON DELETE SET NULL,
    priority_id UUID NOT NULL REFERENCES ticket_priorities(priority_id) ON DELETE RESTRICT,
    status_id UUID NOT NULL REFERENCES ticket_statuses(status_id) ON DELETE RESTRICT,
    affected_device_id UUID REFERENCES stock_devices(device_id) ON DELETE SET NULL,
    current_technician_crm_user_id UUID REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    current_warehouse_crm_user_id UUID REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    resolved_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    
    -- Creador histórico: NOT NULL + ON DELETE RESTRICT
    created_by_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_tickets_client ON tickets(client_id);
CREATE INDEX idx_tickets_location ON tickets(location_id);
CREATE INDEX idx_tickets_category ON tickets(category_id);
CREATE INDEX idx_tickets_status ON tickets(status_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_tickets_priority ON tickets(priority_id);
CREATE INDEX idx_tickets_technician ON tickets(current_technician_crm_user_id);
CREATE INDEX idx_tickets_warehouse ON tickets(current_warehouse_crm_user_id);
CREATE INDEX idx_tickets_created_at ON tickets(created_at);
CREATE INDEX idx_tickets_created_by ON tickets(created_by_crm_user_id);

COMMENT ON TABLE tickets IS 
'Tickets (incidencias/problemas reportados por clientes)';

-- Tabla: ticket_assignments
-- Historial de asignaciones de tickets (técnicos y depósito)
CREATE TABLE ticket_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    assignment_type VARCHAR(50) NOT NULL, -- 'TECHNICIAN', 'WAREHOUSE'
    
    -- Asignado histórico: NOT NULL + ON DELETE RESTRICT
    assigned_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE RESTRICT,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    assigned_by_crm_user_id UUID REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    unassigned_at TIMESTAMPTZ,
    notes TEXT,
    
    CONSTRAINT chk_assignment_type CHECK (assignment_type IN ('TECHNICIAN', 'WAREHOUSE'))
);

CREATE INDEX idx_ticket_assignments_ticket ON ticket_assignments(ticket_id, assigned_at DESC);
CREATE INDEX idx_ticket_assignments_user ON ticket_assignments(assigned_crm_user_id);
CREATE INDEX idx_ticket_assignments_type ON ticket_assignments(assignment_type);

COMMENT ON TABLE ticket_assignments IS 
'Historial de asignaciones de tickets (técnicos y depósito). 
assigned_crm_user_id es NOT NULL + ON DELETE RESTRICT (preservar historial).';

-- Tabla: ticket_resolution_notes
-- Notas de resolución del ticket
CREATE TABLE ticket_resolution_notes (
    note_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    
    -- Creador de nota: NOT NULL + ON DELETE RESTRICT
    created_by_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ticket_resolution_notes_ticket ON ticket_resolution_notes(ticket_id, created_at DESC);

COMMENT ON TABLE ticket_resolution_notes IS 
'Notas de resolución del ticket (comentarios del técnico)';

-- Tabla: ticket_attachments
-- Adjuntos multimedia de tickets
CREATE TABLE ticket_attachments (
    attachment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    file_name VARCHAR(500) NOT NULL,
    file_url VARCHAR(1000) NOT NULL,
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),
    attachment_type VARCHAR(50) NOT NULL, -- 'PHOTO', 'VIDEO', 'DOCUMENT'
    uploaded_by_crm_user_id UUID REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_ticket_attachment_type CHECK (attachment_type IN ('PHOTO', 'VIDEO', 'DOCUMENT'))
);

CREATE INDEX idx_ticket_attachments_ticket ON ticket_attachments(ticket_id);
CREATE INDEX idx_ticket_attachments_uploaded_at ON ticket_attachments(uploaded_at);

COMMENT ON TABLE ticket_attachments IS 
'Adjuntos multimedia de tickets';

-- Tabla: ticket_inventory_requests
-- Solicitudes de materiales desde un ticket
CREATE TABLE ticket_inventory_requests (
    request_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    request_status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    
    -- Solicitante histórico: NOT NULL + ON DELETE RESTRICT
    requested_by_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE RESTRICT,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Revisor opcional: NULL + SET NULL
    reviewed_by_crm_user_id UUID REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,
    
    CONSTRAINT chk_request_status 
        CHECK (request_status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED'))
);

CREATE INDEX idx_ticket_inventory_requests_ticket ON ticket_inventory_requests(ticket_id);
CREATE INDEX idx_ticket_inventory_requests_status ON ticket_inventory_requests(request_status);
CREATE INDEX idx_ticket_inventory_requests_requested_by ON ticket_inventory_requests(requested_by_crm_user_id);

COMMENT ON TABLE ticket_inventory_requests IS 
'Solicitudes de materiales desde ticket (técnico solicita a depósito)';

-- Tabla: ticket_inventory_request_items
-- Items dentro de una solicitud de inventario
CREATE TABLE ticket_inventory_request_items (
    request_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id UUID NOT NULL REFERENCES ticket_inventory_requests(request_id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES inventory_products(product_id) ON DELETE CASCADE,
    quantity_requested DECIMAL(12, 3) NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_quantity_requested CHECK (quantity_requested > 0)
);

CREATE INDEX idx_ticket_inventory_request_items_request ON ticket_inventory_request_items(request_id);
CREATE INDEX idx_ticket_inventory_request_items_product ON ticket_inventory_request_items(product_id);

COMMENT ON TABLE ticket_inventory_request_items IS 
'Productos solicitados en cada request';

-- Tabla: ticket_dispatches
-- Despachos de materiales desde depósito para un ticket
CREATE TABLE ticket_dispatches (
    dispatch_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    request_id UUID REFERENCES ticket_inventory_requests(request_id) ON DELETE SET NULL,
    
    -- Despachador histórico: NOT NULL + ON DELETE RESTRICT
    dispatched_by_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE RESTRICT,
    dispatched_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dispatch_notes TEXT
);

CREATE INDEX idx_ticket_dispatches_ticket ON ticket_dispatches(ticket_id);
CREATE INDEX idx_ticket_dispatches_request ON ticket_dispatches(request_id);
CREATE INDEX idx_ticket_dispatches_dispatched_by ON ticket_dispatches(dispatched_by_crm_user_id);

COMMENT ON TABLE ticket_dispatches IS 
'Despachos de materiales desde depósito (puede o no estar relacionado con request)';

-- Tabla: ticket_dispatch_items
-- Items despachados en cada despacho
CREATE TABLE ticket_dispatch_items (
    dispatch_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dispatch_id UUID NOT NULL REFERENCES ticket_dispatches(dispatch_id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES inventory_products(product_id) ON DELETE CASCADE,
    quantity_dispatched DECIMAL(12, 3) NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_quantity_dispatched CHECK (quantity_dispatched > 0)
);

CREATE INDEX idx_ticket_dispatch_items_dispatch ON ticket_dispatch_items(dispatch_id);
CREATE INDEX idx_ticket_dispatch_items_product ON ticket_dispatch_items(product_id);

COMMENT ON TABLE ticket_dispatch_items IS 
'Productos despachados en cada despacho';

-- =====================================================
-- SECCIÓN 7: TRIGGERS Y FUNCIONES
-- =====================================================

-- Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger a todas las tablas con updated_at
CREATE TRIGGER update_crm_users_updated_at 
    BEFORE UPDATE ON crm_users FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_crm_roles_updated_at 
    BEFORE UPDATE ON crm_roles FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_clients_updated_at 
    BEFORE UPDATE ON clients FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_locations_updated_at 
    BEFORE UPDATE ON locations FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_warehouses_updated_at 
    BEFORE UPDATE ON warehouses FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_inventory_categories_updated_at 
    BEFORE UPDATE ON inventory_categories FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_inventory_products_updated_at 
    BEFORE UPDATE ON inventory_products FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_inventory_stock_updated_at 
    BEFORE UPDATE ON inventory_stock FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stock_devices_updated_at 
    BEFORE UPDATE ON stock_devices FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_task_templates_updated_at 
    BEFORE UPDATE ON task_templates FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at 
    BEFORE UPDATE ON tasks FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subtasks_updated_at 
    BEFORE UPDATE ON subtasks FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ticket_categories_updated_at 
    BEFORE UPDATE ON ticket_categories FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tickets_updated_at 
    BEFORE UPDATE ON tickets FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ticket_resolution_notes_updated_at 
    BEFORE UPDATE ON ticket_resolution_notes FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- DATOS SEMILLA (SEED DATA)
-- =====================================================

-- Almacenes
INSERT INTO warehouses (warehouse_name, address) VALUES
('Depósito Principal', 'Buenos Aires, Argentina');

-- Roles funcionales del CRM
INSERT INTO crm_roles (role_key, role_label, description) VALUES
('admin_crm', 'Administrador del CRM', 'Acceso total al sistema CRM (NO implica platform_admin de auth)'),
('tecnico_campo', 'Técnico de Campo', 'Ejecuta tareas y tickets en ubicaciones del cliente'),
('encargado_deposito', 'Encargado de Depósito', 'Gestiona inventario, despachos y recepciones'),
('dispatcher', 'Despachador/Coordinador', 'Asigna tareas, coordina logística, aprueba solicitudes');

-- Prioridades de tickets
INSERT INTO ticket_priorities (priority_key, priority_label, priority_level) VALUES
('BAJA', 'Baja', 1),
('MEDIA', 'Media', 2),
('ALTA', 'Alta', 3),
('CRITICA', 'Crítica', 4);

-- Estados de tickets
INSERT INTO ticket_statuses (status_key, status_label, status_order, is_final) VALUES
('OPEN', 'Abierto', 1, FALSE),
('IN_PROGRESS', 'En Progreso', 2, FALSE),
('AWAITING_APPROVAL', 'Esperando Aprobación', 3, FALSE),
('RESOLVED', 'Resuelto', 4, FALSE),
('CLOSED', 'Cerrado', 5, TRUE),
('CANCELLED', 'Cancelado', 6, TRUE);

-- =====================================================
-- FIN DEL ESQUEMA
-- =====================================================

-- RESUMEN FINAL:
--
-- SEPARACIÓN DE RESPONSABILIDADES:
-- ✅ auth.microtv.ar: autenticación, contraseñas, sesiones JWT, contexto multi-tenant, roles de identidad
-- ✅ CRM: perfil operativo de usuarios, roles funcionales del CRM, datos de negocio
--
-- INTEGRACIÓN:
-- ✅ auth_user_id es REFERENCIA LÓGICA (NO foreign key física)
-- ✅ Snapshot contextual de auth persistido en crm_users (membership, tenant, roles)
-- ✅ Backend del CRM valida JWT y sincroniza crm_users + contexto automáticamente
-- ✅ Roles de auth (last_auth_roles_json) NO reemplazan crm_roles (roles funcionales locales)
-- ✅ NO hay password_hash, user_sessions, ni lógica de autenticación duplicada
--
-- CORRECCIONES APLICADAS EN V3:
-- ✅ auth_user_id sin FK física (comentarios corregidos)
-- ✅ NOT NULL + ON DELETE resuelto consistentemente (RESTRICT para históricos)
-- ✅ inventory_stock con warehouse_id NOT NULL (tabla warehouses creada)
-- ✅ Constraints secuenciales: UNIQUE(task_id, order_index) en subtasks
-- ✅ Template checklist: template_subtask_checklist_items agregada
-- ✅ Tasks con materiales: task_material_assignments agregada
-- ✅ inventory_movements polimórfico documentado
-- ✅ client_locations.is_primary con índice único parcial
-- ✅ completion_notes obligatorio cuando is_completed = TRUE
--
-- MEJORAS APLICADAS EN V4:
-- ✅ Contexto auth persistido como snapshot en crm_users:
--    - last_auth_membership_id (membership activa en auth)
--    - last_auth_tenant_type (tipo de tenant: company, etc.)
--    - last_auth_tenant_id (ID del tenant en auth)
--    - last_auth_roles_json (array JSON de roles en ese contexto)
--    - last_auth_context_synced_at (timestamp de sincronización)
-- ✅ Comentarios SQL claros explicando que el contexto auth es cache/snapshot
-- ✅ Separación semántica clara: auth roles ≠ crm_roles
-- ✅ Índice compuesto en (last_auth_tenant_type, last_auth_tenant_id)
--
-- USO DEL CONTEXTO AUTH PERSISTIDO:
-- - Trazabilidad: saber bajo qué contexto operó el usuario
-- - Debugging: auditar cambios de membership/tenant
-- - UI: mostrar nombre de empresa/tenant sin consultar auth
-- - Lógica contextual: validar permisos combinando roles auth + crm_roles
-- - NO es autoritativo: el JWT es la fuente de verdad
-- - NO reemplaza validación JWT en cada request
