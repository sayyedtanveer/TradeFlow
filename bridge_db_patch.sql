-- Run this manually if your Phase 3 or Phase 4 tables were generated without the bridge columns.

-- 1. Ensure sales_order_lines can track the created work_order_id
ALTER TABLE sales_order_lines 
ADD COLUMN IF NOT EXISTS work_order_id UUID NULL;

-- 2. Ensure work_orders can track what sales_order_id triggered it
ALTER TABLE work_orders
ADD COLUMN IF NOT EXISTS sales_order_id UUID NULL;

-- 3. Add an index for faster lookups when fulfilling backorders
CREATE INDEX IF NOT EXISTS ix_sales_order_lines_work_order_id ON sales_order_lines(work_order_id);
CREATE INDEX IF NOT EXISTS ix_work_orders_sales_order_id ON work_orders(sales_order_id);
