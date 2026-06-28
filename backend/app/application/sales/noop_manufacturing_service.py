"""No-op manufacturing service stub for distribution/trading system.

After removing manufacturing modules, shortage handling no longer creates work orders.
This stub satisfies the interface expected by InventoryReservationService without
introducing manufacturing dependencies.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID


class NoOpManufacturingService:
    """No-op replacement for SalesManufacturingIntegrationService.

    In a distribution/trading system, shortages are handled via backorders
    rather than manufacturing work orders. This stub simply returns None
    for any work order creation request.
    """

    async def create_work_order(
        self,
        tenant_id: UUID,
        product_id: UUID,
        product_type: str,
        quantity: Decimal,
        uom_id: UUID,
        due_date=None,
        sales_order_id: Optional[UUID] = None,
        sales_order_line_id: Optional[UUID] = None,
    ) -> None:
        """No-op: returns None (no work order created)."""
        return None
