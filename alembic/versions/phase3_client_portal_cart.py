"""Add cart_items table for client portal shopping cart.

Revision ID: phase3_client_portal_cart
Revises: phase2_inventory_reservation_system
Create Date: 2026-06-01 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "phase3_client_portal_cart"
down_revision = "phase2_inventory_reservation_system"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cart_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_type", sa.String(length=50), nullable=False, server_default="material"),
        sa.Column("quantity", sa.Numeric(15, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["sales_clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["materials.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cart_items_tenant_client", "cart_items", ["tenant_id", "client_id"])
    op.create_index("ix_cart_items_product", "cart_items", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_cart_items_product", table_name="cart_items")
    op.drop_index("ix_cart_items_tenant_client", table_name="cart_items")
    op.drop_table("cart_items")
