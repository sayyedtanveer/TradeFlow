"""Add warehouse_id to inventory tables and create warehouse_product_thresholds.

Extends inventory tables with warehouse scoping:
  - Adds nullable warehouse_id FK to stock_levels (backward compatible)
  - Adds nullable warehouse_id FK to inventory_transactions (backward compatible)
  - Creates warehouse_product_thresholds table for per-warehouse reorder thresholds

Revision ID: warehouse_002_add_warehouse_inventory_scoping
Revises: warehouse_001_add_warehouse_tables
Create Date: 2026-06-02 00:01:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "warehouse_002_add_warehouse_inventory_scoping"
down_revision = "warehouse_001_add_warehouse_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add warehouse_id to stock_levels (nullable for backward compatibility)
    op.add_column(
        "stock_levels",
        sa.Column("warehouse_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_stock_levels_warehouse_id",
        "stock_levels",
        "warehouses",
        ["warehouse_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_stock_levels_warehouse_id", "stock_levels", ["warehouse_id"])

    # Add warehouse_id to inventory_transactions (nullable for backward compatibility)
    op.add_column(
        "inventory_transactions",
        sa.Column("warehouse_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_inventory_transactions_warehouse_id",
        "inventory_transactions",
        "warehouses",
        ["warehouse_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_inv_tx_warehouse_id", "inventory_transactions", ["warehouse_id"])

    # Create warehouse_product_thresholds table
    op.create_table(
        "warehouse_product_thresholds",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), nullable=False),
        sa.Column("reorder_threshold", sa.Integer(), nullable=False, server_default="0"),
        # Soft delete
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["materials.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "tenant_id", "warehouse_id", "product_id",
            name="uq_warehouse_product_threshold_tenant_wh_product",
        ),
    )
    op.create_index("ix_warehouse_product_thresholds_tenant_id", "warehouse_product_thresholds", ["tenant_id"])
    op.create_index("ix_warehouse_product_thresholds_warehouse_id", "warehouse_product_thresholds", ["warehouse_id"])
    op.create_index("ix_warehouse_product_thresholds_product_id", "warehouse_product_thresholds", ["product_id"])


def downgrade() -> None:
    # Drop warehouse_product_thresholds
    op.drop_index("ix_warehouse_product_thresholds_product_id", table_name="warehouse_product_thresholds")
    op.drop_index("ix_warehouse_product_thresholds_warehouse_id", table_name="warehouse_product_thresholds")
    op.drop_index("ix_warehouse_product_thresholds_tenant_id", table_name="warehouse_product_thresholds")
    op.drop_table("warehouse_product_thresholds")

    # Remove warehouse_id from inventory_transactions
    op.drop_index("ix_inv_tx_warehouse_id", table_name="inventory_transactions")
    op.drop_constraint("fk_inventory_transactions_warehouse_id", "inventory_transactions", type_="foreignkey")
    op.drop_column("inventory_transactions", "warehouse_id")

    # Remove warehouse_id from stock_levels
    op.drop_index("ix_stock_levels_warehouse_id", table_name="stock_levels")
    op.drop_constraint("fk_stock_levels_warehouse_id", "stock_levels", type_="foreignkey")
    op.drop_column("stock_levels", "warehouse_id")
