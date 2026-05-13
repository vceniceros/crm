-- =============================================================================
-- 20260513_ticket_required_materials.sql
-- Materiales opcionales requeridos al crear tickets
-- =============================================================================

CREATE TABLE IF NOT EXISTS ticket_required_materials (
    ticket_required_material_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES inventory_products(product_id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ticket_required_materials_ticket
    ON ticket_required_materials (ticket_id);

CREATE INDEX IF NOT EXISTS idx_ticket_required_materials_product
    ON ticket_required_materials (product_id);
