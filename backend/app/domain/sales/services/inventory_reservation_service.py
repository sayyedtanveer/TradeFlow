"""Inventory reservation domain service.

Implements the inventory reservation system for sales orders:
- Reserves ordered quantities upon order confirmation to prevent overselling
- Releases reservations on order cancellation
- Available quantity = current_stock - reserved_quantity

Requirements: 5.7, 6.3, 6.13
"""

import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class InsufficientInventoryError(ValueError):
    """Raised when available inventory is insufficient for reservation."""

    def __init__(self, product_id: UUID, requested: Decimal, available: Decimal):
        self.product_id = product_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient inventory for product {product_id}: "
            f"requested {requested}, available {available}"
        )


class InventoryReservationService:
    """
    Inventory reservation service for sales orders.
    
    Responsibilities:
    - Reserve stock when order is confirmed (Req 5.7)
    - Release stock when order is cancelled (Req 6.3, 6.13)
    - Prevent overselling via available_stock check (current_stock - reserved_stock)
    """

    def __init__(self, inventory_service, *_args, **_kwargs):
        """
        Initialize inventory reservation service.
        
        Args:
            inventory_service: External inventory domain service (SalesInventoryIntegrationService)
        """
        self.inventory_service = inventory_service

    async def reserve_for_order_line(
        self,
        tenant_id: UUID,
        product_id: UUID,
        product_type: str,
        uom_id: UUID,
        quantity: Decimal,
        sales_order_id: UUID,
        sales_order_line_id: UUID,
        delivery_date,
        warehouse_id: Optional[UUID] = None,
    ) -> tuple[Decimal, Decimal, Optional[UUID]]:
        """
        Reserve inventory for an order line.
        
        Allocation strategy:
        1. Check available stock (current_stock - reserved_stock)
        2. If sufficient: reserve the full quantity
        3. If insufficient: reserve what's available, report shortage
        
        The caller is responsible for deciding whether to reject the order
        or allow a partial backorder based on the shortage quantity.
        
        Args:
            tenant_id: Tenant ID
            product_id: Product ID
            product_type: Product type ("variant" or "finished_product")
            uom_id: Unit of measure ID
            quantity: Quantity to reserve
            sales_order_id: Sales order ID
            sales_order_line_id: Sales order line ID
            delivery_date: Delivery date
            
        Returns:
            Tuple of (allocated_qty, shortage_qty, warehouse_id).
            warehouse_id is None when no single-warehouse assignment is determined.
            
        Raises:
            InsufficientInventoryError: If no stock is available at all and
                the caller needs to handle a complete shortage.
            ValueError: If reservation fails for other reasons.
        """
        try:
            # Get available stock (= current_stock - reserved_stock)
            available = await self.inventory_service.get_available_stock(
                tenant_id=tenant_id,
                product_id=product_id,
                product_type=product_type,
            )
            
            allocated_qty = min(available, quantity)
            shortage_qty = quantity - allocated_qty
            
            # Reserve the allocated quantity to prevent overselling
            if allocated_qty > 0:
                await self.inventory_service.reserve_stock(
                    tenant_id=tenant_id,
                    product_id=product_id,
                    product_type=product_type,
                    quantity=allocated_qty,
                    uom_id=uom_id,
                    reference_type="sales_order_line",
                    reference_id=sales_order_line_id,
                    warehouse_id=warehouse_id,
                    order_id=sales_order_id,
                )
                logger.info(
                    "Reserved %s units for order line %s (product %s). Shortage: %s",
                    allocated_qty, sales_order_line_id, product_id, shortage_qty,
                )
            else:
                logger.warning(
                    "No available stock for product %s. Requested: %s, Available: %s",
                    product_id, quantity, available,
                )
            
            # Return None for warehouse_id - determined by inventory validation handler
            return allocated_qty, shortage_qty, None
            
        except InsufficientInventoryError:
            raise
        except Exception as e:
            raise ValueError(
                f"Failed to reserve inventory for product {product_id}: {str(e)}"
            )

    async def release_for_order(
        self,
        tenant_id: UUID,
        sales_order_id: UUID,
        lines,
    ) -> None:
        """
        Release all reserved inventory for an order (on cancellation).
        
        Called when an order is cancelled (Req 6.3, 6.13) to release
        reserved_stock back to available pool, preventing phantom reservations
        from blocking future orders.
        
        Args:
            tenant_id: Tenant ID
            sales_order_id: Sales order ID
            lines: List of SalesOrderLine entities with allocated_quantity
        """
        for line in lines:
            if line.allocated_quantity > 0:
                try:
                    await self.inventory_service.release_stock(
                        tenant_id=tenant_id,
                        reference_type="sales_order_line",
                        reference_id=line.id,
                        quantity=line.allocated_quantity,
                    )
                    logger.info(
                        "Released %s reserved units for order line %s (order %s)",
                        line.allocated_quantity, line.id, sales_order_id,
                    )
                except Exception as e:
                    # Log but don't fail the cancellation - best effort release
                    logger.warning(
                        "Failed to release stock for line %s: %s", line.id, str(e)
                    )

    async def record_shipment(
        self,
        tenant_id: UUID,
        sales_order_line_id: UUID,
        shipped_qty: Decimal,
    ) -> None:
        """
        Record shipment, converting reservation to actual stock reduction.
        
        When goods are shipped, the reservation is consumed:
        - reserved_stock decreases by shipped_qty
        - current_stock decreases by shipped_qty
        
        Args:
            tenant_id: Tenant ID
            sales_order_line_id: Sales order line ID
            shipped_qty: Quantity shipped
        """
        try:
            await self.inventory_service.fulfill_reservation(
                tenant_id=tenant_id,
                reference_type="sales_order_line",
                reference_id=sales_order_line_id,
                quantity=shipped_qty,
            )
            logger.info(
                "Fulfilled reservation of %s units for order line %s",
                shipped_qty, sales_order_line_id,
            )
        except Exception as e:
            raise ValueError(
                f"Failed to record shipment for line {sales_order_line_id}: {str(e)}"
            )

    async def check_availability(
        self,
        tenant_id: UUID,
        product_id: UUID,
        product_type: str,
        quantity: Decimal,
    ) -> tuple[bool, Decimal]:
        """
        Check if sufficient stock is available for a given quantity.
        
        Available = current_stock - reserved_stock.
        
        Args:
            tenant_id: Tenant ID
            product_id: Product ID
            product_type: Product type
            quantity: Requested quantity
            
        Returns:
            Tuple of (is_sufficient: bool, available_qty: Decimal)
        """
        available = await self.inventory_service.get_available_stock(
            tenant_id=tenant_id,
            product_id=product_id,
            product_type=product_type,
        )
        return available >= quantity, available
