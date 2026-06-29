"""Phase 3: Add warehouse_id and order_id to inventory_reservations.

Revision ID: phase3_inventory_reservation_warehouse_scope
Revises: order_status_003_distribution_workflow
Create Date: 2026-06-01 00:00:00.000000

Changes:
  - Add warehouse_id column to inventory_reservations (FK to warehouses)
  - Add order_id column to inventory_reservations (for bulk release on cancellation)
  - Add index on (tenant_id, warehouse_id) for warehouse-scoped queries
  - Add index on order_id for order-level reservation lookups
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'phase3_inventory_reservation_warehouse_scope'
down_revision = 'order_status_003_distribution_workflow'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add warehouse_id column
    op.add_column(
        'inventory_reservations',
        sa.Column(
            'warehouse_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('warehouses.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )
    # Add order_id column for efficient order-level release
    op.add_column(
        'inventory_reservations',
        sa.Column(
            'order_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    # Add returned_quantity column (was missing from original migration)
    op.add_column(
        'inventory_reservations',
        sa.Column(
            'returned_quantity',
            sa.Numeric(15, 3),
            nullable=False,
            server_default='0',
        ),
    )
    # Add index for warehouse-scoped reservation queries
    op.create_index(
        'ix_ir_tenant_warehouse',
        'inventory_reservations',
        ['tenant_id', 'warehouse_id'],
    )
    # Add index for order-level reservation lookups
    op.create_index(
        'ix_ir_order',
        'inventory_reservations',
        ['order_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_ir_order', table_name='inventory_reservations')
    op.drop_index('ix_ir_tenant_warehouse', table_name='inventory_reservations')
    op.drop_column('inventory_reservations', 'returned_quantity')
    op.drop_column('inventory_reservations', 'order_id')
    op.drop_column('inventory_reservations', 'warehouse_id')
