"""Replace OrderStatus enum with distribution-focused statuses and add workflow columns.

Updates the sales_orders table:
  - Widens the status column to String(50) to accommodate longer status values
  - Migrates existing order statuses to the new distribution-focused values
  - Adds assigned_warehouse_id (FK to warehouses), assigned_at, accepted_at,
    dispatched_at, hold_reason columns for distribution workflow tracking

Revision ID: order_status_003_distribution_workflow
Revises: warehouse_002_add_warehouse_inventory_scoping
Create Date: 2026-06-02 00:02:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "order_status_003_distribution_workflow"
down_revision = "warehouse_002_add_warehouse_inventory_scoping"
branch_labels = None
depends_on = None


# Mapping of old manufacturing statuses to new distribution statuses for backward compat
OLD_TO_NEW_STATUS_MAP = {
    "DRAFT": "PENDING_INVENTORY_VALIDATION",
    "PENDING_APPROVAL": "PENDING_INVENTORY_VALIDATION",
    "APPROVED": "PENDING_INVENTORY_VALIDATION",
    "REJECTED": "CANCELLED",
    "WORK_ORDER_CREATED": "ASSIGNED",
    "CONFIRMED": "ASSIGNED",
    "PROCESSING": "PICKING",
    "PRODUCTION": "PICKING",
    "READY": "READY_FOR_DISPATCH",
    "READY_FOR_DISPATCH": "READY_FOR_DISPATCH",
    "SHIPPED": "DISPATCHED",
    "DELIVERED": "DISPATCHED",
    "INVOICED": "INVOICED",
    "PAYMENT_RECEIVED": "INVOICED",
    "COMPLETED": "INVOICED",
    "CANCELLED": "CANCELLED",
}


def upgrade() -> None:
    # 1. Widen the status column to accommodate longer new status values
    op.alter_column(
        "sales_orders",
        "status",
        type_=sa.String(50),
        existing_type=sa.String(20),
        existing_nullable=False,
    )

    # 2. Migrate existing status values to new distribution statuses
    for old_status, new_status in OLD_TO_NEW_STATUS_MAP.items():
        op.execute(
            sa.text(
                f"UPDATE sales_orders SET status = :new_status WHERE status = :old_status"
            ).bindparams(new_status=new_status, old_status=old_status)
        )

    # 3. Add distribution workflow columns
    op.add_column(
        "sales_orders",
        sa.Column("assigned_warehouse_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_sales_orders_assigned_warehouse_id",
        "sales_orders",
        "warehouses",
        ["assigned_warehouse_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_sales_order_assigned_warehouse_id",
        "sales_orders",
        ["assigned_warehouse_id"],
    )

    op.add_column(
        "sales_orders",
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sales_orders",
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sales_orders",
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sales_orders",
        sa.Column("hold_reason", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    # Remove distribution workflow columns
    op.drop_column("sales_orders", "hold_reason")
    op.drop_column("sales_orders", "dispatched_at")
    op.drop_column("sales_orders", "accepted_at")
    op.drop_index("ix_sales_order_assigned_warehouse_id", table_name="sales_orders")
    op.drop_constraint("fk_sales_orders_assigned_warehouse_id", "sales_orders", type_="foreignkey")
    op.drop_column("sales_orders", "assigned_at")
    op.drop_column("sales_orders", "assigned_warehouse_id")

    # Revert status column width
    op.alter_column(
        "sales_orders",
        "status",
        type_=sa.String(20),
        existing_type=sa.String(50),
        existing_nullable=False,
    )

    # Note: Data migration back from new → old statuses is not automated in downgrade.
    # Manual intervention may be needed for existing orders.
