"""Add warehouses and warehouse_user_assignments tables.

Creates the core warehouse tables for the Warehouse bounded context:
  - warehouses: warehouse profiles with address, contact info, soft delete
  - warehouse_user_assignments: links users to warehouses (1 user = 1 warehouse)

Revision ID: warehouse_001_add_warehouse_tables
Revises: drop_manufacturing_tables
Create Date: 2026-06-02 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "warehouse_001_add_warehouse_tables"
down_revision = "drop_manufacturing_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create warehouses table
    op.create_table(
        "warehouses",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        # Address fields (flattened from Address value object)
        sa.Column("address_street", sa.String(length=255), nullable=False),
        sa.Column("address_city", sa.String(length=100), nullable=False),
        sa.Column("address_region", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("address_postal_code", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("address_country", sa.String(length=100), nullable=False),
        # Contact info
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        # Status
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        # Soft delete
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_warehouse_tenant_name"),
    )
    op.create_index("ix_warehouses_tenant_id", "warehouses", ["tenant_id"])
    op.create_index("ix_warehouses_is_deleted", "warehouses", ["is_deleted"])

    # Create warehouse_user_assignments table
    op.create_table(
        "warehouse_user_assignments",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("assigned_by", UUID(as_uuid=True), nullable=True),
        # Soft delete
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_warehouse_user_assignment_tenant_user"),
    )
    op.create_index("ix_warehouse_user_assignments_tenant_id", "warehouse_user_assignments", ["tenant_id"])
    op.create_index("ix_warehouse_user_assignments_warehouse_id", "warehouse_user_assignments", ["warehouse_id"])
    op.create_index("ix_warehouse_user_assignments_user_id", "warehouse_user_assignments", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_warehouse_user_assignments_user_id", table_name="warehouse_user_assignments")
    op.drop_index("ix_warehouse_user_assignments_warehouse_id", table_name="warehouse_user_assignments")
    op.drop_index("ix_warehouse_user_assignments_tenant_id", table_name="warehouse_user_assignments")
    op.drop_table("warehouse_user_assignments")
    op.drop_index("ix_warehouses_is_deleted", table_name="warehouses")
    op.drop_index("ix_warehouses_tenant_id", table_name="warehouses")
    op.drop_table("warehouses")
