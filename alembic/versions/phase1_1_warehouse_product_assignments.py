"""Phase 1.1: Add warehouse_product_assignments table.

Creates the warehouse_product_assignments table for tracking which products
are available at which warehouses. This is the foundation for:
  - Order allocation (finding warehouses for product fulfillment)
  - Warehouse product management (admin can assign/unassign products)
  - Stock aggregation queries (checking product availability across warehouses)

Revision ID: phase1_1_warehouse_product_assignments
Revises: wh005_pick_lists
Create Date: 2026-06-29 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "phase1_1_warehouse_product_assignments"
down_revision = "wh005_pick_lists"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create warehouse_product_assignments table
    op.create_table(
        "warehouse_product_assignments",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("default_reorder_level", sa.Integer(), nullable=False, server_default="0"),
        # Soft delete
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["item_templates.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "warehouse_id", "product_id", name="uq_warehouse_product_assignment_tenant_wh_product"),
    )
    
    # Create indexes for query performance
    op.create_index("ix_warehouse_product_assignments_tenant_id", "warehouse_product_assignments", ["tenant_id"])
    op.create_index("ix_warehouse_product_assignments_warehouse_id", "warehouse_product_assignments", ["warehouse_id"])
    op.create_index("ix_warehouse_product_assignments_product_id", "warehouse_product_assignments", ["product_id"])
    op.create_index("ix_warehouse_product_assignments_is_available", "warehouse_product_assignments", ["is_available"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_warehouse_product_assignments_is_available", table_name="warehouse_product_assignments")
    op.drop_index("ix_warehouse_product_assignments_product_id", table_name="warehouse_product_assignments")
    op.drop_index("ix_warehouse_product_assignments_warehouse_id", table_name="warehouse_product_assignments")
    op.drop_index("ix_warehouse_product_assignments_tenant_id", table_name="warehouse_product_assignments")
    
    # Drop table
    op.drop_table("warehouse_product_assignments")
