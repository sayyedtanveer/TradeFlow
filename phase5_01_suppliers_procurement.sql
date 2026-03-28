-- Phase 5 — Suppliers & Procurement (run after Phase 4)
-- Execute SQL files in order: 01 → 02 → 03 → 04
-- Uses existing `materials` table (not raw_materials) for line items.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS po_number_sequences (
    tenant_id UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    current_value INTEGER NOT NULL DEFAULT 0
);

-- ── Suppliers ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS suppliers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    contact_person VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    gst VARCHAR(50),
    payment_terms VARCHAR(100),
    performance_rating NUMERIC(5, 2),
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_suppliers_tenant_code UNIQUE (tenant_id, code)
);
CREATE INDEX IF NOT EXISTS ix_suppliers_tenant ON suppliers(tenant_id);
CREATE INDEX IF NOT EXISTS ix_suppliers_active ON suppliers(tenant_id, is_active) WHERE is_deleted = false;

-- ── Purchase orders ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS purchase_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    po_number VARCHAR(40) NOT NULL,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    order_date DATE NOT NULL DEFAULT (CURRENT_DATE),
    expected_delivery DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'sent', 'acknowledged', 'partial', 'received', 'closed')),
    total_amount NUMERIC(18, 4) NOT NULL DEFAULT 0,
    notes TEXT,
    created_by UUID NOT NULL REFERENCES users(id),
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_po_tenant_number UNIQUE (tenant_id, po_number)
);
CREATE INDEX IF NOT EXISTS ix_po_tenant_supplier ON purchase_orders(tenant_id, supplier_id);
CREATE INDEX IF NOT EXISTS ix_po_status ON purchase_orders(tenant_id, status);

-- ── PO lines ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS purchase_order_lines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    purchase_order_id UUID NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    material_id UUID NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
    quantity NUMERIC(15, 3) NOT NULL CHECK (quantity > 0),
    received_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0 CHECK (received_quantity >= 0),
    unit_price NUMERIC(18, 4) NOT NULL DEFAULT 0,
    line_total NUMERIC(18, 4) NOT NULL DEFAULT 0,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_pol_po ON purchase_order_lines(purchase_order_id);
CREATE INDEX IF NOT EXISTS ix_pol_material ON purchase_order_lines(material_id);

-- ── Supplier price history ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS supplier_price_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    material_id UUID NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
    unit_price NUMERIC(18, 4) NOT NULL,
    effective_from DATE NOT NULL DEFAULT CURRENT_DATE,
    effective_to DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_sph_supplier ON supplier_price_history(supplier_id);
CREATE INDEX IF NOT EXISTS ix_sph_material ON supplier_price_history(material_id);
