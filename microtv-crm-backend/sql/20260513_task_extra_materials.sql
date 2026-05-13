-- =============================================================================
-- 20260513_task_extra_materials.sql
-- Materiales opcionales adicionales al crear pedidos
-- =============================================================================

CREATE TABLE IF NOT EXISTS task_extra_materials (
    task_extra_material_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES inventory_products(product_id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_task_extra_materials_task
    ON task_extra_materials (task_id);

CREATE INDEX IF NOT EXISTS idx_task_extra_materials_product
    ON task_extra_materials (product_id);
