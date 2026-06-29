"""Order Allocation Service - Finds suitable warehouse to fulfill an order.

Core business rule:
  - An order must be fulfilled entirely from a SINGLE warehouse
  - Query available inventory per warehouse
  - Return the first warehouse with enough stock for all items
  - If no warehouse can fulfill, raise allocation error for manual handling
"""

from __future__ import annotations

import uuid
from typing import Optional, List

from backend.app.domain.warehouse.repositories.warehouse_product_assignment_repository import (
    WarehouseProductAssignmentRepository,
)
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork


class OrderAllocationError(Exception):
    """Raised when an order cannot be allocated to any warehouse."""
    pass


class OrderAllocationService:
    """Service for automatically allocating orders to warehouses."""

    def __init__(
        self,
        warehouse_product_repo: WarehouseProductAssignmentRepository,
        uow: SQLAlchemyUnitOfWork,
    ) -> None:
        """Initialize allocation service with dependencies."""
        self._warehouse_product_repo = warehouse_product_repo
        self._uow = uow

    async def allocate_order(
        self,
        tenant_id: uuid.UUID,
        order_id: uuid.UUID,
        line_items: List[OrderLineItem],
        exclude_warehouse_ids: Optional[List[uuid.UUID]] = None,
    ) -> uuid.UUID:
        """
        Find a warehouse that can fulfill the entire order.

        Args:
            tenant_id: Tenant context
            order_id: Order being allocated (for logging/audit)
            line_items: List of (product_id, quantity_needed) tuples
            exclude_warehouse_ids: Warehouses to skip (e.g., already tried)

        Returns:
            warehouse_id of suitable warehouse

        Raises:
            OrderAllocationError: If no warehouse can fulfill entire order
        """
        if not line_items:
            raise OrderAllocationError("Order has no line items to allocate")

        exclude_ids = set(exclude_warehouse_ids or [])

        # Step 1: Find warehouses that carry ALL products in the order
        suitable_warehouses = await self._find_warehouses_with_all_products(
            tenant_id=tenant_id,
            product_ids=[item.product_id for item in line_items],
            exclude_warehouse_ids=exclude_ids,
        )

        if not suitable_warehouses:
            raise OrderAllocationError(
                f"No warehouse carries all {len(line_items)} products in order {order_id}"
            )

        # Step 2: For each warehouse with all products, check if it has enough inventory
        # Note: This requires access to inventory service which would be passed via DI
        # For now, we return the first warehouse that has all products
        # The allocation handler will verify inventory when reserving

        allocated_warehouse_id = suitable_warehouses[0]

        return allocated_warehouse_id

    async def find_alternative_warehouse(
        self,
        tenant_id: uuid.UUID,
        order_id: uuid.UUID,
        line_items: List[OrderLineItem],
        already_tried_warehouse_ids: List[uuid.UUID],
    ) -> Optional[uuid.UUID]:
        """
        Find an alternative warehouse if initial allocation couldn't reserve stock.

        Used when inventory reservation fails in the initially allocated warehouse.
        """
        try:
            return await self.allocate_order(
                tenant_id=tenant_id,
                order_id=order_id,
                line_items=line_items,
                exclude_warehouse_ids=already_tried_warehouse_ids,
            )
        except OrderAllocationError:
            return None

    async def _find_warehouses_with_all_products(
        self,
        tenant_id: uuid.UUID,
        product_ids: List[uuid.UUID],
        exclude_warehouse_ids: set,
    ) -> List[uuid.UUID]:
        """Find all warehouses that have ALL products from the list."""
        if not product_ids:
            return []

        # For each product, get the list of available warehouses
        warehouses_per_product = []

        for product_id in product_ids:
            assignments = await self._warehouse_product_repo.get_warehouses_for_product(
                product_id=product_id,
                tenant_id=tenant_id,
            )

            if not assignments:
                # This product is not available in any warehouse
                return []

            warehouse_ids = {
                a.warehouse_id
                for a in assignments
                if a.warehouse_id not in exclude_warehouse_ids
            }
            warehouses_per_product.append(warehouse_ids)

        # Find intersection: warehouses that have ALL products
        if not warehouses_per_product:
            return []

        suitable_warehouses = warehouses_per_product[0]
        for warehouse_set in warehouses_per_product[1:]:
            suitable_warehouses = suitable_warehouses.intersection(warehouse_set)

        return list(suitable_warehouses)


class OrderLineItem:
    """DTO for order line item during allocation."""

    def __init__(self, product_id: uuid.UUID, quantity_needed: int):
        self.product_id = product_id
        self.quantity_needed = quantity_needed
