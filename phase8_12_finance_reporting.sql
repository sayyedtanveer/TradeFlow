-- ============================================================
-- PHASE 8-12: Finance, Reporting, Notifications, Audit, Jobs
-- MedTrack ERP — Migration Script
-- ============================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- PHASE 8: FINANCE MODULE
-- ============================================================

-- Invoices (AR — Accounts Receivable)
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_number VARCHAR(50) NOT NULL,
    sales_order_id UUID REFERENCES sales_orders(id) ON DELETE RESTRICT,
    client_id UUID NOT NULL REFERENCES sales_clients(id) ON DELETE RESTRICT,
    -- Snapshot client info at invoice time
    client_name VARCHAR(255) NOT NULL,
    client_address TEXT,
    client_gst_number VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT','SENT','PARTIAL','PAID','OVERDUE','CANCELLED','VOID')),
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    -- Financial totals
    subtotal DECIMAL(15,2) NOT NULL DEFAULT 0,
    discount_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    tax_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    grand_total DECIMAL(15,2) NOT NULL DEFAULT 0,
    paid_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    balance_due DECIMAL(15,2) GENERATED ALWAYS AS (grand_total - paid_amount) STORED,
    -- Metadata
    notes TEXT,
    terms TEXT,
    created_by UUID REFERENCES users(id),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_invoice_tenant_number UNIQUE (tenant_id, invoice_number)
);

CREATE INDEX IF NOT EXISTS idx_invoices_tenant_id ON invoices(tenant_id);
CREATE INDEX IF NOT EXISTS idx_invoices_client_id ON invoices(client_id);
CREATE INDEX IF NOT EXISTS idx_invoices_sales_order ON invoices(sales_order_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_due_date ON invoices(due_date);

-- Invoice Lines (snapshot of SO lines — decoupled from live SO)
CREATE TABLE IF NOT EXISTS invoice_lines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    product_id UUID NOT NULL,
    product_type VARCHAR(20) NOT NULL CHECK (product_type IN ('finished', 'variant', 'material')),
    description TEXT,
    quantity INT NOT NULL,
    unit_price DECIMAL(15,2) NOT NULL,
    discount_amount DECIMAL(15,2) DEFAULT 0,
    tax_rate DECIMAL(5,2) DEFAULT 0,
    tax_amount DECIMAL(15,2) DEFAULT 0,
    total DECIMAL(15,2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_invoice_lines_invoice_id ON invoice_lines(invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoice_lines_tenant ON invoice_lines(tenant_id);

-- Supplier Invoices (AP — Accounts Payable)
CREATE TABLE IF NOT EXISTS supplier_invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_number VARCHAR(50) NOT NULL,
    supplier_invoice_ref VARCHAR(100),  -- supplier's own reference
    purchase_order_id UUID REFERENCES purchase_orders(id) ON DELETE RESTRICT,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    -- Snapshot supplier info
    supplier_name VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','PARTIAL','PAID','OVERDUE','CANCELLED')),
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    -- Financial totals
    subtotal DECIMAL(15,2) NOT NULL DEFAULT 0,
    tax_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    grand_total DECIMAL(15,2) NOT NULL DEFAULT 0,
    paid_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    notes TEXT,
    created_by UUID REFERENCES users(id),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_supplier_invoice_tenant_number UNIQUE (tenant_id, invoice_number)
);

CREATE INDEX IF NOT EXISTS idx_supplier_invoices_tenant ON supplier_invoices(tenant_id);
CREATE INDEX IF NOT EXISTS idx_supplier_invoices_supplier ON supplier_invoices(supplier_id);
CREATE INDEX IF NOT EXISTS idx_supplier_invoices_status ON supplier_invoices(status);

-- Payments (AR)
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    payment_number VARCHAR(50) NOT NULL,
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE RESTRICT,
    client_id UUID NOT NULL REFERENCES sales_clients(id) ON DELETE RESTRICT,
    amount DECIMAL(15,2) NOT NULL CHECK (amount > 0),
    payment_date DATE NOT NULL,
    payment_method VARCHAR(30) NOT NULL DEFAULT 'BANK_TRANSFER'
        CHECK (payment_method IN ('BANK_TRANSFER','CASH','CHEQUE','ONLINE','UPI','OTHER')),
    reference_number VARCHAR(100),  -- bank ref / cheque number
    notes TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_payment_tenant_number UNIQUE (tenant_id, payment_number)
);

CREATE INDEX IF NOT EXISTS idx_payments_tenant ON payments(tenant_id);
CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_payments_client ON payments(client_id);

-- Supplier Payments (AP)
CREATE TABLE IF NOT EXISTS supplier_payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    payment_number VARCHAR(50) NOT NULL,
    supplier_invoice_id UUID NOT NULL REFERENCES supplier_invoices(id) ON DELETE RESTRICT,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    amount DECIMAL(15,2) NOT NULL CHECK (amount > 0),
    payment_date DATE NOT NULL,
    payment_method VARCHAR(30) NOT NULL DEFAULT 'BANK_TRANSFER'
        CHECK (payment_method IN ('BANK_TRANSFER','CASH','CHEQUE','ONLINE','UPI','OTHER')),
    reference_number VARCHAR(100),
    notes TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_supplier_payment_tenant_number UNIQUE (tenant_id, payment_number)
);

CREATE INDEX IF NOT EXISTS idx_supplier_payments_tenant ON supplier_payments(tenant_id);
CREATE INDEX IF NOT EXISTS idx_supplier_payments_supplier ON supplier_payments(supplier_id);

-- Financial Transactions Ledger
CREATE TABLE IF NOT EXISTS financial_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    reference_type VARCHAR(30) NOT NULL
        CHECK (reference_type IN ('invoice', 'payment', 'supplier_invoice', 'supplier_payment', 'credit_note', 'debit_note')),
    reference_id UUID NOT NULL,
    account_type VARCHAR(30) NOT NULL DEFAULT 'RECEIVABLE'
        CHECK (account_type IN ('RECEIVABLE','PAYABLE','REVENUE','EXPENSE','CASH')),
    debit DECIMAL(15,2) DEFAULT 0,
    credit DECIMAL(15,2) DEFAULT 0,
    description TEXT,
    meta JSONB DEFAULT '{}',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_financial_transactions_reference ON financial_transactions(reference_type, reference_id);
CREATE INDEX IF NOT EXISTS idx_financial_transactions_tenant ON financial_transactions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_financial_transactions_date ON financial_transactions(created_at);

-- ============================================================
-- PHASE 10: NOTIFICATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL
        CHECK (type IN ('LOW_STOCK','PO_RECEIVED','NCR_CREATED','INVOICE_OVERDUE','WORK_ORDER','PAYMENT_RECEIVED','SYSTEM')),
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    reference_type VARCHAR(50),
    reference_id UUID,
    is_read BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    email_sent BOOLEAN DEFAULT FALSE,
    email_sent_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_tenant ON notifications(tenant_id);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type);

-- ============================================================
-- PHASE 11: BACKGROUND JOBS
-- ============================================================

CREATE TABLE IF NOT EXISTS background_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL
        CHECK (job_type IN ('mrp_run','overdue_invoices','report_refresh','low_stock_alert','email_notify')),
    status VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending','running','completed','failed')),
    payload JSONB DEFAULT '{}',
    result JSONB,
    error TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_background_jobs_status ON background_jobs(status);
CREATE INDEX IF NOT EXISTS idx_background_jobs_type ON background_jobs(job_type);

-- ============================================================
-- PHASE 9: MATERIALIZED VIEWS FOR REPORTING
-- ============================================================

-- Inventory Turnover
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_inventory_turnover AS
SELECT 
    tenant_id,
    material_id,
    material_type,
    SUM(ABS(quantity)) as total_consumed,
    COUNT(DISTINCT date_trunc('month', created_at)) as months_count
FROM inventory_transactions
WHERE transaction_type IN ('ISSUE', 'issue', 'CONSUMPTION')
GROUP BY tenant_id, material_id, material_type;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_inventory_turnover ON mv_inventory_turnover(tenant_id, material_id, material_type);

-- Work Order Efficiency
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_work_order_efficiency AS
SELECT 
    tenant_id,
    date_trunc('month', created_at)::date as month,
    SUM(produced_quantity) as total_produced,
    SUM(scrap_quantity) as total_scrap,
    ROUND(SUM(scrap_quantity)::numeric / NULLIF(SUM(produced_quantity + scrap_quantity), 0) * 100, 2) as scrap_percentage
FROM work_orders
WHERE status = 'completed'
GROUP BY tenant_id, date_trunc('month', created_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_work_order_efficiency ON mv_work_order_efficiency(tenant_id, month);

-- Sales Revenue Summary
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_sales_revenue AS
SELECT 
    so.tenant_id,
    date_trunc('month', so.created_at)::date as month,
    COUNT(DISTINCT so.id) as order_count,
    SUM(so.grand_total) as total_revenue,
    SUM(so.discount_amount) as total_discount,
    SUM(so.tax_amount) as total_tax
FROM sales_orders so
WHERE so.status NOT IN ('CANCELLED') AND so.is_deleted = false
GROUP BY so.tenant_id, date_trunc('month', so.created_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_sales_revenue ON mv_sales_revenue(tenant_id, month);

-- AR Aging (snapshot — refreshed by background job)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_ar_aging AS
SELECT
    i.tenant_id,
    i.client_id,
    i.client_name,
    COUNT(*) FILTER (WHERE (CURRENT_DATE - i.due_date) <= 0) as current_count,
    SUM(i.balance_due) FILTER (WHERE (CURRENT_DATE - i.due_date) <= 0) as current_amount,
    COUNT(*) FILTER (WHERE (CURRENT_DATE - i.due_date) BETWEEN 1 AND 30) as overdue_1_30,
    SUM(i.balance_due) FILTER (WHERE (CURRENT_DATE - i.due_date) BETWEEN 1 AND 30) as amount_1_30,
    COUNT(*) FILTER (WHERE (CURRENT_DATE - i.due_date) BETWEEN 31 AND 60) as overdue_31_60,
    SUM(i.balance_due) FILTER (WHERE (CURRENT_DATE - i.due_date) BETWEEN 31 AND 60) as amount_31_60,
    COUNT(*) FILTER (WHERE (CURRENT_DATE - i.due_date) > 60) as overdue_60_plus,
    SUM(i.balance_due) FILTER (WHERE (CURRENT_DATE - i.due_date) > 60) as amount_60_plus,
    SUM(i.balance_due) as total_outstanding
FROM invoices i
WHERE i.status NOT IN ('PAID','CANCELLED','VOID') AND i.is_deleted = false
GROUP BY i.tenant_id, i.client_id, i.client_name;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_ar_aging ON mv_ar_aging(tenant_id, client_id);

-- ============================================================
-- TRIGGERS: auto-update updated_at
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_invoices_updated_at
    BEFORE UPDATE ON invoices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER trg_supplier_invoices_updated_at
    BEFORE UPDATE ON supplier_invoices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- SEQUENCES for invoice/payment numbering
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS invoice_seq START 1000 INCREMENT 1;
CREATE SEQUENCE IF NOT EXISTS supplier_invoice_seq START 1000 INCREMENT 1;
CREATE SEQUENCE IF NOT EXISTS payment_seq START 1000 INCREMENT 1;
CREATE SEQUENCE IF NOT EXISTS supplier_payment_seq START 1000 INCREMENT 1;
