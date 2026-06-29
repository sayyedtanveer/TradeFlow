"""Pick list generation service.

Generates a pick list automatically when a warehouse user accepts an order
(ASSIGNED → ACCEPTED transition). The pick list contains product names, SKUs,
quantities, and storage locations for each order line item.

Requirements: 7.2, 7.3
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.warehouse.entities.pick_list import (
    PickList,
    PickListLine,
    PickListStatus,
)
from backend.app.infrastructure.persistence.models.pick_list_model import (
    PickListModel,
    PickListLineModel,
)
from backend.app.infrastructure.persistence.models.sales_models import (
    SalesOrderModel,
    SalesOrderLineModel,
)
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.stock_level_model import StockLevelModel
from backend.app.infrastructure.persistence.models.location_model import LocationModel


class PickListService:
    """Service for generating and managing pick lists.

    This service is responsible for:
    - Generating a pick list from an order's line items when the order is accepted
    - Resolving product names, SKUs, and storage locations from the database
    - Persisting the generated pick list
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def generate_pick_list(
        self,
        *,
        tenant_id: uuid.UUID,
        order_id: uuid.UUID,
        warehouse_id: uuid.UUID,
    ) -> PickList:
        """Generate a pick list for an accepted order.

        Queries the order's line items and resolves product details (name, SKU)
        and storage locations from the inventory/material data.

        Args:
            tenant_id: The tenant owning the order.
            order_id: The sales order ID.
            warehouse_id: The warehouse where picking will occur.

        Returns:
            The generated PickList domain entity.

        Raises:
            ValueError: If the order is not found or already has a pick list.
        """
        # Check if a pick list already exists for this order
        existing_stmt = select(PickListModel).where(
            PickListModel.tenant_id == tenant_id,
            PickListModel.order_id == order_id,
            PickListModel.is_deleted == False,  # noqa: E712
        )
        existing_result = await self._session.execute(existing_stmt)
        if existing_result.scalar_one_or_none() is not None:
            raise ValueError(
                f"A pick list already exists for order {order_id}"
            )

        # Fetch the order and its line items
        order_stmt = select(SalesOrderModel).where(
            SalesOrderModel.id == order_id,
            SalesOrderModel.tenant_id == tenant_id,
            SalesOrderModel.is_deleted == False,  # noqa: E712
        )
        order_result = await self._session.execute(order_stmt)
        order = order_result.scalar_one_or_none()
        if order is None:
            raise ValueError(f"Order {order_id} not found")

        # Fetch order lines
        lines_stmt = select(SalesOrderLineModel).where(
            SalesOrderLineModel.sales_order_id == order_id,
        )
        lines_result = await self._session.execute(lines_stmt)
        order_lines = lines_result.scalars().all()

        if not order_lines:
            raise ValueError(f"Order {order_id} has no line items")

        # Create the pick list aggregate
        pick_list = PickList(
            tenant_id=tenant_id,
            order_id=order_id,
            warehouse_id=warehouse_id,
            status=PickListStatus.PENDING,
        )

        # For each order line, resolve product details and storage location
        for order_line in order_lines:
            product_name, sku, storage_location = await self._resolve_product_details(
                product_id=order_line.product_id,
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
            )

            pick_line = PickListLine(
                tenant_id=tenant_id,
                pick_list_id=pick_list.id,
                order_line_id=order_line.id,
                product_id=order_line.product_id,
                product_name=product_name,
                sku=sku,
                quantity=int(order_line.quantity),
                storage_location=storage_location,
            )
            pick_list.add_line(pick_line)

        # Persist the pick list
        await self._persist_pick_list(pick_list)

        return pick_list

    async def get_pick_list_by_order(
        self,
        *,
        tenant_id: uuid.UUID,
        order_id: uuid.UUID,
    ) -> Optional[PickList]:
        """Retrieve a pick list by order ID.

        Args:
            tenant_id: The tenant owning the order.
            order_id: The sales order ID.

        Returns:
            The PickList domain entity, or None if not found.
        """
        stmt = select(PickListModel).where(
            PickListModel.tenant_id == tenant_id,
            PickListModel.order_id == order_id,
            PickListModel.is_deleted == False,  # noqa: E712
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return self._to_domain(model)

    async def _resolve_product_details(
        self,
        *,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID,
        warehouse_id: uuid.UUID,
    ) -> tuple[str, str, Optional[str]]:
        """Resolve product name, SKU, and storage location.

        Args:
            product_id: The product/material ID.
            tenant_id: The tenant ID for scoping.
            warehouse_id: The warehouse where stock is located.

        Returns:
            Tuple of (product_name, sku, storage_location).
        """
        # Fetch product details
        product_stmt = select(MaterialModel).where(
            MaterialModel.id == product_id,
            MaterialModel.tenant_id == tenant_id,
        )
        product_result = await self._session.execute(product_stmt)
        product = product_result.scalar_one_or_none()

        if product is None:
            # Fallback if product not found (shouldn't happen in normal flow)
            return ("Unknown Product", "UNKNOWN", None)

        product_name = product.name
        sku = product.code  # 'code' is the SKU field in MaterialModel

        # Resolve storage location from stock levels
        storage_location = await self._resolve_storage_location(
            product_id=product_id,
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
        )

        return (product_name, sku, storage_location)

    async def _resolve_storage_location(
        self,
        *,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID,
        warehouse_id: uuid.UUID,
    ) -> Optional[str]:
        """Resolve the storage location for a product in the given warehouse.

        Looks up the stock level record for the product in the warehouse
        and resolves the location name.

        Args:
            product_id: The product/material ID.
            tenant_id: The tenant ID.
            warehouse_id: The warehouse ID.

        Returns:
            The location name/code, or None if not found.
        """
        # Find stock level for this product in this warehouse
        stock_stmt = select(StockLevelModel).where(
            StockLevelModel.tenant_id == tenant_id,
            StockLevelModel.material_id == product_id,
            StockLevelModel.warehouse_id == warehouse_id,
            StockLevelModel.is_deleted == False,  # noqa: E712
        )
        stock_result = await self._session.execute(stock_stmt)
        stock_level = stock_result.scalars().first()

        if stock_level is None or stock_level.location_id is None:
            # Fallback: check product's default location
            product_stmt = select(MaterialModel.location_id).where(
                MaterialModel.id == product_id,
            )
            product_result = await self._session.execute(product_stmt)
            location_id = product_result.scalar_one_or_none()
            if location_id is None:
                return None
        else:
            location_id = stock_level.location_id

        # Resolve location name
        loc_stmt = select(LocationModel).where(LocationModel.id == location_id)
        loc_result = await self._session.execute(loc_stmt)
        location = loc_result.scalar_one_or_none()

        if location is None:
            return None

        return location.name

    async def _persist_pick_list(self, pick_list: PickList) -> None:
        """Persist a pick list and its lines to the database.

        Args:
            pick_list: The PickList domain entity to persist.
        """
        pick_list_model = PickListModel(
            id=pick_list.id,
            tenant_id=pick_list.tenant_id,
            order_id=pick_list.order_id,
            warehouse_id=pick_list.warehouse_id,
            status=pick_list.status.value,
            created_at=pick_list.created_at,
            completed_at=pick_list.completed_at,
        )
        self._session.add(pick_list_model)

        for line in pick_list.lines:
            line_model = PickListLineModel(
                id=line.id,
                pick_list_id=pick_list.id,
                order_line_id=line.order_line_id,
                product_id=line.product_id,
                product_name=line.product_name,
                sku=line.sku,
                quantity=line.quantity,
                storage_location=line.storage_location,
                is_picked=line.is_picked,
                picked_at=line.picked_at,
            )
            self._session.add(line_model)

        await self._session.flush()

    def _to_domain(self, model: PickListModel) -> PickList:
        """Convert a PickListModel to a PickList domain entity.

        Args:
            model: The SQLAlchemy model instance.

        Returns:
            The PickList domain entity.
        """
        lines = [
            PickListLine(
                id=line_model.id,
                tenant_id=model.tenant_id,
                pick_list_id=model.id,
                order_line_id=line_model.order_line_id,
                product_id=line_model.product_id,
                product_name=line_model.product_name,
                sku=line_model.sku,
                quantity=line_model.quantity,
                storage_location=line_model.storage_location,
                is_picked=line_model.is_picked,
                picked_at=line_model.picked_at,
            )
            for line_model in model.lines
        ]

        return PickList(
            id=model.id,
            tenant_id=model.tenant_id,
            order_id=model.order_id,
            warehouse_id=model.warehouse_id,
            status=PickListStatus(model.status),
            lines=lines,
            created_at=model.created_at,
            completed_at=model.completed_at,
        )
