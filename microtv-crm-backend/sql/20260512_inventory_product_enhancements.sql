-- Columna: stock minimo configurable por producto
ALTER TABLE inventory_products
  ADD COLUMN IF NOT EXISTS minimum_stock INTEGER NOT NULL DEFAULT 3
    CONSTRAINT inventory_products_minimum_stock_positive CHECK (minimum_stock >= 1);

-- Columna: letra de estanteria (A-Z)
ALTER TABLE inventory_products
  ADD COLUMN IF NOT EXISTS shelf_id VARCHAR(1) NULL
    CONSTRAINT inventory_products_shelf_id_alpha CHECK (shelf_id ~ '^[A-Z]$');

-- Columna: numero de altura de estante (entero positivo)
ALTER TABLE inventory_products
  ADD COLUMN IF NOT EXISTS shelf_height SMALLINT NULL
    CONSTRAINT inventory_products_shelf_height_positive CHECK (shelf_height >= 1);