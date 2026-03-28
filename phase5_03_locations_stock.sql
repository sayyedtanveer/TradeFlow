-- Phase 5 — Location types extension + location-based stock balances

-- Extend location `type` to support supply-chain locations (stored in existing `type` column)
-- No CHECK constraint on locations.type in base schema — add optional code for ERP codes

ALTER TABLE locations ADD COLUMN IF NOT EXISTS code VARCHAR(50);
CREATE UNIQUE INDEX IF NOT EXISTS uq_locations_tenant_code ON locations(tenant_id, code) WHERE code IS NOT NULL AND is_deleted = false;

-- Stock by location and quality bucket (mandatory for GRN / quarantine / inspection)
CREATE TABLE IF NOT EXISTS stock_levels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    material_id UUID NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
    location_id UUID NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
    stock_status VARCHAR(30) NOT NULL
        CHECK (stock_status IN ('available', 'pending_inspection', 'quarantine')),
    quantity NUMERIC(18, 4) NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_stock_levels_bucket UNIQUE (tenant_id, material_id, location_id, stock_status)
);
CREATE INDEX IF NOT EXISTS ix_stock_levels_tenant_mat ON stock_levels(tenant_id, material_id);
CREATE INDEX IF NOT EXISTS ix_stock_levels_loc ON stock_levels(location_id);
