"""Drop manufacturing tables.

Remove all manufacturing-specific database tables as part of the
TradeFlow ERP transformation from manufacturing to distribution/trading.

Tables dropped:
  - material_shortages
  - pick_list_lines
  - pick_lists
  - material_consumption_records
  - production_records
  - job_cards
  - work_order_materials
  - work_orders
  - wo_number_sequences
  - mrp_suggestions
  - bom_operations
  - bom_lines
  - boms
  - operations
  - workstations
  - inspection_details
  - quality_inspections
  - non_conformance_reports
  - quarantine_releases
  - inspection_templates
  - subcontract_material_issues
  - subcontract_orders
  - subcontract_number_sequences

Also removes the work_order_id column from sales_order_lines (retained table).

Revision ID: drop_manufacturing_tables
Revises: a62c0f8c9545
Create Date: 2026-06-01 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "drop_manufacturing_tables"
down_revision = "a62c0f8c9545"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Remove work_order_id column from retained sales_order_lines table ──
    # This column linked sales order lines to manufacturing work orders.
    # No FK constraint exists (was never added), so just drop the column.
    op.drop_column("sales_order_lines", "work_order_id")

    # ── 2. Drop material shortages (FK to work_orders) ──────────────────────
    op.drop_index("ix_ms_tenant_wo", table_name="material_shortages")
    op.drop_index("ix_ms_tenant_material", table_name="material_shortages")
    op.drop_index("ix_ms_status", table_name="material_shortages")
    op.drop_table("material_shortages")

    # ── 3. Drop manufacturing pick list tables (FK to work_orders) ────────────
    op.drop_table("pick_list_lines")
    op.drop_table("pick_lists")

    # ── 4. Drop material consumption records (FK to work_orders) ──────────────
    op.drop_index("ix_mcr_tenant_wo", table_name="material_consumption_records")
    op.drop_table("material_consumption_records")

    # ── 5. Drop production records (FK to work_orders) ────────────────────────
    op.drop_index("ix_production_records_work_order_id", table_name="production_records")
    op.drop_table("production_records")

    # ── 6. Drop job cards (FK to work_orders and operations) ──────────────────
    op.drop_index("ix_job_cards_work_order_id", table_name="job_cards")
    op.drop_table("job_cards")

    # ── 7. Drop work order materials (FK to work_orders) ──────────────────────
    op.drop_table("work_order_materials")

    # ── 8. Drop work orders (FK to boms) ──────────────────────────────────────
    op.drop_index("ix_work_orders_tenant_id", table_name="work_orders")
    op.drop_index("ix_work_orders_tenant_status", table_name="work_orders")
    op.drop_index("ix_work_orders_tenant_due", table_name="work_orders")
    op.drop_table("work_orders")

    # ── 9. Drop WO number sequences ──────────────────────────────────────────
    op.drop_table("wo_number_sequences")

    # ── 10. Drop MRP suggestions ─────────────────────────────────────────────
    op.drop_index("ix_mrp_suggestions_tenant_id", table_name="mrp_suggestions")
    op.drop_index("ix_mrp_suggestions_tenant_status", table_name="mrp_suggestions")
    op.drop_index("ix_mrp_suggestions_tenant_material", table_name="mrp_suggestions")
    op.drop_index("ix_mrp_suggestions_created_at", table_name="mrp_suggestions")
    op.drop_table("mrp_suggestions")

    # ── 11. Drop BOM operations (FK to boms and operations) ──────────────────
    op.drop_index("ix_bom_operations_bom_id", table_name="bom_operations")
    op.drop_index("ix_bom_operations_operation_id", table_name="bom_operations")
    op.drop_index("ix_bom_operations_tenant_id", table_name="bom_operations")
    op.drop_table("bom_operations")

    # ── 12. Drop BOM lines (FK to boms) ──────────────────────────────────────
    op.drop_index("ix_bom_lines_bom_id", table_name="bom_lines")
    op.drop_index("ix_bom_line_tenant_bom", table_name="bom_lines")
    op.drop_table("bom_lines")

    # ── 13. Drop BOMs ─────────────────────────────────────────────────────────
    op.drop_index("ix_bom_tenant_product", table_name="boms")
    op.drop_table("boms")

    # ── 14. Drop operations (FK to workstations) ─────────────────────────────
    op.drop_index("ix_operations_tenant_id", table_name="operations")
    op.drop_index("ix_operations_workstation_id", table_name="operations")
    op.drop_table("operations")

    # ── 15. Drop workstations ─────────────────────────────────────────────────
    op.drop_index("ix_workstations_code", table_name="workstations")
    op.drop_index("ix_workstations_tenant_id", table_name="workstations")
    op.drop_table("workstations")

    # ── 16. Drop QC / inspection tables ───────────────────────────────────────
    # quarantine_releases has FK to non_conformance_reports — drop first
    op.drop_table("quarantine_releases")
    op.drop_table("inspection_details")
    op.drop_table("non_conformance_reports")
    op.drop_table("quality_inspections")
    op.drop_table("inspection_templates")

    # ── 17. Drop subcontracting tables (manufacturing-specific) ───────────────
    op.drop_table("subcontract_material_issues")
    op.drop_table("subcontract_orders")
    op.drop_table("subcontract_number_sequences")


def downgrade() -> None:
    # Manufacturing module removal is permanent. This migration is not reversible.
    raise NotImplementedError(
        "Downgrade is not supported. Manufacturing tables have been permanently "
        "removed as part of the TradeFlow ERP transformation."
    )
