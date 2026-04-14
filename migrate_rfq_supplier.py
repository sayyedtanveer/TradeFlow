"""Run the phase-8 RFQ + invoice-dispute migration using asyncpg."""
import asyncio, os, sys

import asyncpg

# strip the +asyncpg driver prefix that SQLAlchemy uses
RAW_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:123@localhost:5432/medtrack",
).replace("postgresql+asyncpg://", "postgresql://")

SQL_MAIN = """
CREATE TABLE IF NOT EXISTS rfq_number_sequences (
    tenant_id     UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    current_value BIGINT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS rfqs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    rfq_number          VARCHAR(40) NOT NULL,
    material_request_id UUID REFERENCES material_requests(id) ON DELETE SET NULL,
    title               VARCHAR(255),
    status              VARCHAR(20) NOT NULL DEFAULT 'draft',
    deadline            DATE,
    notes               TEXT,
    awarded_supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    awarded_po_id       UUID REFERENCES purchase_orders(id) ON DELETE SET NULL,
    created_by          UUID NOT NULL REFERENCES users(id),
    is_deleted          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_rfq_tenant ON rfqs(tenant_id);

CREATE TABLE IF NOT EXISTS rfq_lines (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    rfq_id      UUID NOT NULL REFERENCES rfqs(id) ON DELETE CASCADE,
    material_id UUID NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
    quantity    NUMERIC(15,3) NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_rfq_lines_rfq ON rfq_lines(rfq_id);

CREATE TABLE IF NOT EXISTS rfq_suppliers (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    rfq_id       UUID NOT NULL REFERENCES rfqs(id) ON DELETE CASCADE,
    supplier_id  UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    status       VARCHAR(20) NOT NULL DEFAULT 'invited',
    quotation_id UUID REFERENCES supplier_quotations(id) ON DELETE SET NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_rfq_supplier_rfq ON rfq_suppliers(rfq_id, supplier_id);

CREATE TABLE IF NOT EXISTS invoice_disputes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    supplier_invoice_id UUID NOT NULL REFERENCES supplier_invoices(id) ON DELETE CASCADE,
    disputed_amount     NUMERIC(15,2) NOT NULL,
    reason              TEXT NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'open',
    resolution_notes    TEXT,
    raised_by_supplier  BOOLEAN NOT NULL DEFAULT TRUE,
    resolved_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    resolved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_invoice_dispute_invoice ON invoice_disputes(supplier_invoice_id);
"""

SQL_RFQ_ID_COL = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'supplier_quotations' AND column_name = 'rfq_id'
    ) THEN
        ALTER TABLE supplier_quotations
          ADD COLUMN rfq_id UUID REFERENCES rfqs(id) ON DELETE SET NULL;
    END IF;
END $$;
"""


async def main() -> None:
    print(f"Connecting to: {RAW_URL}")
    try:
        conn = await asyncpg.connect(RAW_URL)
        await conn.execute(SQL_MAIN)
        await conn.execute(SQL_RFQ_ID_COL)
        await conn.close()
        print("Migration complete — RFQ and invoice_dispute tables created/verified.")
    except Exception as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
