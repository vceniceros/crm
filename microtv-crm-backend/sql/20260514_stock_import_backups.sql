CREATE TABLE IF NOT EXISTS stock_import_batches (
    import_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    filename VARCHAR(255) NOT NULL,
    created_by_crm_user_id UUID NULL REFERENCES crm_users(crm_user_id),
    confirmed_by_crm_user_id UUID NULL REFERENCES crm_users(crm_user_id),
    total_rows INTEGER NOT NULL DEFAULT 0,
    valid_rows INTEGER NOT NULL DEFAULT 0,
    invalid_rows INTEGER NOT NULL DEFAULT 0,
    created_count INTEGER NOT NULL DEFAULT 0,
    updated_count INTEGER NOT NULL DEFAULT 0,
    total_import_stock INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confirmed_at TIMESTAMPTZ NULL
);

CREATE TABLE IF NOT EXISTS stock_import_rows (
    import_row_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    import_id UUID NOT NULL REFERENCES stock_import_batches(import_id) ON DELETE CASCADE,
    row_number INTEGER NOT NULL,
    image_url VARCHAR(500) NOT NULL DEFAULT '',
    product_code VARCHAR(100) NOT NULL,
    product_name VARCHAR(255) NOT NULL DEFAULT '',
    category_name VARCHAR(255) NOT NULL DEFAULT '',
    category_id UUID NULL REFERENCES inventory_categories(category_id),
    imported_stock INTEGER NOT NULL DEFAULT 0,
    old_stock INTEGER NOT NULL DEFAULT 0,
    new_stock INTEGER NOT NULL DEFAULT 0,
    shelf_id VARCHAR(1) NULL,
    shelf_height INTEGER NULL,
    is_new_product BOOLEAN NOT NULL DEFAULT FALSE,
    is_valid BOOLEAN NOT NULL DEFAULT FALSE,
    errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    product_id UUID NULL REFERENCES inventory_products(product_id)
);

CREATE TABLE IF NOT EXISTS stock_backups (
    backup_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    import_id UUID NOT NULL UNIQUE REFERENCES stock_import_batches(import_id),
    created_by_crm_user_id UUID NULL REFERENCES crm_users(crm_user_id),
    rolled_back_by_crm_user_id UUID NULL REFERENCES crm_users(crm_user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rolled_back_at TIMESTAMPTZ NULL
);

CREATE TABLE IF NOT EXISTS stock_backup_rows (
    backup_row_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backup_id UUID NOT NULL REFERENCES stock_backups(backup_id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES inventory_products(product_id),
    product_code VARCHAR(100) NULL,
    product_name VARCHAR(255) NOT NULL,
    category_id UUID NULL REFERENCES inventory_categories(category_id),
    image_url VARCHAR(500) NULL,
    current_stock INTEGER NOT NULL DEFAULT 0,
    shelf_id VARCHAR(1) NULL,
    shelf_height INTEGER NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_stock_import_batches_status ON stock_import_batches(status);
CREATE INDEX IF NOT EXISTS idx_stock_import_rows_import_id ON stock_import_rows(import_id);
CREATE INDEX IF NOT EXISTS idx_stock_import_rows_product_code ON stock_import_rows(product_code);
CREATE INDEX IF NOT EXISTS idx_stock_backups_import_id ON stock_backups(import_id);
CREATE INDEX IF NOT EXISTS idx_stock_backup_rows_backup_id ON stock_backup_rows(backup_id);
CREATE INDEX IF NOT EXISTS idx_stock_backup_rows_product_id ON stock_backup_rows(product_id);
