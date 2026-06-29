"""Add pick_lists and pick_list_lines tables for warehouse fulfilment.

Revision ID: wh005_pick_lists
Revises: order_status_003_distribution_workflow
Create Date: 2025-01-27

This migration drops the old manufacturing-era pick_lists/pick_list_lines tables
(which referenced work_orders) and creates new distribution-focused tables
that reference sales_orders for the fulfilment workflow.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers
revision = "wh005_pick_lists"
down_revision = None
branch_labels = ("pick_lists",)
depends_on = None


def upgrade() -> None:
    """Create pick_lists and pick_list_lines tables for distribution fulfilment."""

    # Drop old manufacturing-era pick list tables if they exist
    op.execute("DROP TABLE IF EXISTS pick_list_lines CASCADE")
    op.execute("DROP TABLE IF EXISTS pick_lists CASCADE")

    # Create new pick_lists table
    op.create_table(
        "pick_lists",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "order_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sales_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "warehouse_id",
            UUID(as_uuid=True),
            sa.ForeignKey("warehouses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Indexes for pick_lists
    op.create_index("ix_pick_lists_tenant_id", "pick_lists", ["tenant_id"])
    op.create_index("ix_pick_lists_order_id", "pick_lists", ["order_id"])
    op.create_index("ix_pick_lists_warehouse_id", "pick_lists", ["warehouse_id"])
    op.create_index("ix_pick_lists_status", "pick_lists", ["status"])

    # Unique constraint: one pick list per order per tenant
    op.create_unique_constraint(
        "uq_pick_list_tenant_order", "pick_lists", ["tenant_id", "order_id"]
    )

    # Create pick_list_lines table
    op.create_table(
        "pick_list_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "pick_list_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pick_lists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "order_line_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sales_order_lines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("product_id", UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("sku", sa.String(50), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("storage_location", sa.String(255), nullable=True),
        sa.Column("is_picked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("picked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Indexes for pick_list_lines
    op.create_index(
        "ix_pick_list_lines_pick_list_id", "pick_list_lines", ["pick_list_id"]
    )
    op.create_index(
        "ix_pick_list_lines_product_id", "pick_list_lines", ["product_id"]
    )
    op.create_index(
        "ix_pick_list_lines_order_line_id", "pick_list_lines", ["order_line_id"]
    )


def downgrade() -> None:
    """Drop pick_list_lines and pick_lists tables."""
    op.drop_table("pick_list_lines")
    op.drop_table("pick_lists")
