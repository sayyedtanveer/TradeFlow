-- Phase 4: Work Order & Shop Floor
-- Run this manually against the MedTrack DB

-- 1. WO Number Sequences
CREATE TABLE IF NOT EXISTS wo_number_sequences (
    tenant_id UUID PRIMARY KEY,
    current_value INTEGER NOT NULL DEFAULT 0
);

-- 2. Work Orders
CREATE TABLE IF NOT EXISTS work_orders (
    id UUID PRIMARY KEY,
    wo_number VARCHAR(30) NOT NULL,
    tenant_id UUID NOT NULL,
    product_id UUID NOT NULL,
    bom_id UUID NOT NULL,
    sales_order_id UUID,
    planned_quantity NUMERIC(15, 3) NOT NULL,
    produced_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
    scrap_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'PLANNED',
    priority VARCHAR(10) NOT NULL DEFAULT 'NORMAL',
    start_date DATE NOT NULL,
    due_date DATE NOT NULL,
    notes TEXT,
    created_by UUID NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_work_orders_bom FOREIGN KEY (bom_id) REFERENCES boms(id) ON DELETE RESTRICT,
    CONSTRAINT fk_work_orders_product FOREIGN KEY (product_id) REFERENCES item_variants(id) ON DELETE RESTRICT,
    CONSTRAINT uq_work_order_tenant_number UNIQUE (tenant_id, wo_number),
    CONSTRAINT ck_work_order_status CHECK (status IN ('PLANNED', 'RELEASED', 'IN_PROGRESS', 'COMPLETED', 'CLOSED')),
    CONSTRAINT ck_work_order_priority CHECK (priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT'))
);
CREATE INDEX IF NOT EXISTS ix_work_orders_tenant_id ON work_orders(tenant_id);
CREATE INDEX IF NOT EXISTS ix_work_orders_tenant_status ON work_orders(tenant_id, status);
CREATE INDEX IF NOT EXISTS ix_work_orders_tenant_due ON work_orders(tenant_id, due_date);

-- 3. Work Order Materials (BOM Snapshot)
CREATE TABLE IF NOT EXISTS work_order_materials (
    id UUID PRIMARY KEY,
    work_order_id UUID NOT NULL,
    material_id UUID NOT NULL,
    unit_id UUID NOT NULL,
    required_quantity NUMERIC(15, 3) NOT NULL,
    issued_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
    CONSTRAINT fk_womat_work_order FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    CONSTRAINT fk_womat_material FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE RESTRICT,
    CONSTRAINT fk_womat_unit FOREIGN KEY (unit_id) REFERENCES units_of_measure(id)
);
CREATE INDEX IF NOT EXISTS ix_wo_materials_work_order_id ON work_order_materials(work_order_id);

-- 4. Job Cards (Operation Snapshot)
CREATE TABLE IF NOT EXISTS job_cards (
    id UUID PRIMARY KEY,
    work_order_id UUID NOT NULL,
    operation_id UUID NOT NULL,
    sequence INTEGER NOT NULL,
    assigned_to UUID,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    remarks TEXT,
    CONSTRAINT fk_jobcard_work_order FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    CONSTRAINT fk_jobcard_operation FOREIGN KEY (operation_id) REFERENCES operations(id) ON DELETE RESTRICT,
    CONSTRAINT ck_job_card_status CHECK (status IN ('PENDING', 'IN_PROGRESS', 'DONE'))
);
CREATE INDEX IF NOT EXISTS ix_job_cards_work_order_id ON job_cards(work_order_id);

-- 5. Production Records
CREATE TABLE IF NOT EXISTS production_records (
    id UUID PRIMARY KEY,
    work_order_id UUID NOT NULL,
    produced_quantity NUMERIC(15, 3) NOT NULL,
    scrap_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
    recorded_by UUID NOT NULL,
    notes TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_prodrecord_work_order FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_production_records_work_order_id ON production_records(work_order_id);
-- 1. Ensure sales_order_lines can track the created work_order_id
ALTER TABLE sales_order_lines ADD COLUMN IF NOT EXISTS work_order_id UUID NULL;

-- 2. Ensure work_orders can track what sales_order_id triggered it
ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS sales_order_id UUID NULL;

-- 3. Add an index for faster lookups when fulfilling backorders
CREATE INDEX IF NOT EXISTS ix_sales_order_lines_work_order_id ON sales_order_lines(work_order_id);
CREATE INDEX IF NOT EXISTS ix_work_orders_sales_order_id ON work_orders(sales_order_id);
