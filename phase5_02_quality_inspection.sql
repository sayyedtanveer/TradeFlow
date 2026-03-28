-- Phase 5 — Quality, inspection templates, NCR, quarantine releases

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Inspection templates ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS inspection_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    parameters JSONB NOT NULL DEFAULT '[]',
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_insp_tpl_tenant ON inspection_templates(tenant_id);

-- ── Material inspection flags (uses `materials` table) ─────────────────────
ALTER TABLE materials ADD COLUMN IF NOT EXISTS inspection_required BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE materials ADD COLUMN IF NOT EXISTS inspection_template_id UUID REFERENCES inspection_templates(id);
ALTER TABLE materials ADD COLUMN IF NOT EXISTS safety_stock NUMERIC(18, 4);
ALTER TABLE materials ADD COLUMN IF NOT EXISTS lead_time_days INTEGER;

-- ── Quality inspections ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quality_inspections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    reference_type VARCHAR(40) NOT NULL CHECK (reference_type IN ('purchase_receipt', 'work_order')),
    reference_id UUID NOT NULL,
    inspection_date DATE NOT NULL DEFAULT CURRENT_DATE,
    inspector_id UUID REFERENCES users(id),
    result VARCHAR(20) NOT NULL CHECK (result IN ('pass', 'fail', 'rework')),
    remarks TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_qi_tenant_ref ON quality_inspections(tenant_id, reference_type, reference_id);

-- ── Non-conformance (NCR) ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS non_conformance_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    inspection_id UUID REFERENCES quality_inspections(id) ON DELETE SET NULL,
    ncr_type VARCHAR(20) NOT NULL CHECK (ncr_type IN ('rework', 'scrap', 'reject')),
    reason TEXT,
    action_taken TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ncr_tenant ON non_conformance_reports(tenant_id);

-- ── Inspection line details ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS inspection_details (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    inspection_id UUID NOT NULL REFERENCES quality_inspections(id) ON DELETE CASCADE,
    parameter VARCHAR(255) NOT NULL,
    measured_value VARCHAR(255),
    tolerance_min NUMERIC(18, 6),
    tolerance_max NUMERIC(18, 6),
    is_passed BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS ix_insp_det_inspection ON inspection_details(inspection_id);

-- ── Quarantine releases ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quarantine_releases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    ncr_id UUID NOT NULL REFERENCES non_conformance_reports(id) ON DELETE CASCADE,
    released_by UUID REFERENCES users(id),
    released_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    new_location_id UUID REFERENCES locations(id),
    reason TEXT
);
CREATE INDEX IF NOT EXISTS ix_qr_ncr ON quarantine_releases(ncr_id);
