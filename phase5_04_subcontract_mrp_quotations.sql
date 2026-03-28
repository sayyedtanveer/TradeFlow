-- Phase 5 — Subcontracting, MRP material requests, supplier quotations

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS subcontract_number_sequences (
    tenant_id UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    current_value INTEGER NOT NULL DEFAULT 0
);

-- ── Material requests (MRP) ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS material_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    item_id UUID NOT NULL,
    item_type VARCHAR(30) NOT NULL CHECK (item_type IN ('material', 'product')),
    required_quantity NUMERIC(15, 3) NOT NULL,
    fulfilled_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
    required_by DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'partial', 'fulfilled', 'cancelled')),
    source_ref_type VARCHAR(40),
    source_ref_id UUID,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_mr_tenant_status ON material_requests(tenant_id, status);

-- ── Subcontract orders ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subcontract_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    order_number VARCHAR(40) NOT NULL,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    product_id UUID NOT NULL,
    product_type VARCHAR(20) NOT NULL DEFAULT 'variant' CHECK (product_type IN ('variant', 'material')),
    quantity NUMERIC(15, 3) NOT NULL CHECK (quantity > 0),
    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'issued', 'in_progress', 'received', 'closed')),
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_subco_tenant_number UNIQUE (tenant_id, order_number)
);
CREATE INDEX IF NOT EXISTS ix_subco_supplier ON subcontract_orders(supplier_id);

-- ── Material issues to subcontractor ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subcontract_material_issues (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    subcontract_order_id UUID NOT NULL REFERENCES subcontract_orders(id) ON DELETE CASCADE,
    material_id UUID NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
    quantity NUMERIC(15, 3) NOT NULL CHECK (quantity > 0),
    batch_number VARCHAR(80),
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_smi_order ON subcontract_material_issues(subcontract_order_id);

-- ── Supplier quotations (portal) ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS supplier_quotations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    purchase_order_id UUID REFERENCES purchase_orders(id) ON DELETE SET NULL,
    material_id UUID NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
    quantity NUMERIC(15, 3) NOT NULL,
    unit_price NUMERIC(18, 4) NOT NULL,
    valid_until DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'submitted', 'accepted', 'rejected')),
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_sq_supplier ON supplier_quotations(supplier_id);
CREATE INDEX IF NOT EXISTS ix_sq_status ON supplier_quotations(status);

-- ── Link portal users to suppliers ─────────────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_users_supplier ON users(supplier_id) WHERE supplier_id IS NOT NULL;
