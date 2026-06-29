"""Sales Order Allocation Command Handlers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from backend.app.application.sales.commands.order_allocation_commands import (
    AllocateOrderCommand,
    AssignOrderToWarehouseCommand,
    ReassignOrderToWarehouseCommand,
    ReleaseOrderFromWarehouseCommand,
)
from backend.app.application.sales.services.order_allocation_service import (
    OrderAllocationService,
    OrderAllocationError,
    OrderLineItem,
)
from backend.app.domain.sales.repositories.sales_order_repository import (
    SalesOrderRepository,
)
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork


# ── DTOs ──────────────────────────────────────────────────────────────────────

@dataclass
class OrderAllocationResult:
    order_id: str
    allocated_warehouse_id: str
    status: str  # "allocated", "released", "reassigned"
    message: str


# ── Command Handlers ──────────────────────────────────────────────────────────

class AllocateOrderCommandHandler:
    """Handler for AllocateOrderCommand - Auto-allocate order to suitable warehouse."""

    def __init__(
        self,
        allocation_service: OrderAllocationService,
        sales_order_repo: SalesOrderRepository,
        uow: SQLAlchemyUnitOfWork,
    ) -> None:
        self._allocation_service = allocation_service
        self._sales_order_repo = sales_order_repo
        self._uow = uow

    async def handle(self, cmd: AllocateOrderCommand) -> OrderAllocationResult:
        """Automatically allocate order to a warehouse."""
        # Get the order to see current state
        order = await self._sales_order_repo.get_by_id(cmd.order_id, cmd.tenant_id)
        if not order:
            raise ValueError(f"Order {cmd.order_id} not found")

        # Check if already allocated
        if order.assigned_warehouse_id:
            return OrderAllocationResult(
                order_id=str(cmd.order_id),
                allocated_warehouse_id=str(order.assigned_warehouse_id),
                status="allocated",
                message="Order already allocated",
            )

        # Convert line items to service format
        line_items = [
            OrderLineItem(
                product_id=item.product_id,
                quantity_needed=item.quantity,
            )
            for item in cmd.line_items
        ]

        # Call allocation service
        try:
            warehouse_id = await self._allocation_service.allocate_order(
                tenant_id=cmd.tenant_id,
                order_id=cmd.order_id,
                line_items=line_items,
                exclude_warehouse_ids=cmd.exclude_warehouse_ids,
            )
        except OrderAllocationError as e:
            raise ValueError(f"Could not allocate order: {str(e)}")

        # Update order with allocated warehouse
        order.assigned_warehouse_id = warehouse_id
        order.assigned_at = datetime.now(timezone.utc)

        await self._sales_order_repo.save(order)
        await self._uow.commit()

        return OrderAllocationResult(
            order_id=str(cmd.order_id),
            allocated_warehouse_id=str(warehouse_id),
            status="allocated",
            message=f"Order allocated to warehouse {warehouse_id}",
        )


class AssignOrderToWarehouseCommandHandler:
    """Handler for AssignOrderToWarehouseCommand - Manually assign order to warehouse."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        uow: SQLAlchemyUnitOfWork,
    ) -> None:
        self._sales_order_repo = sales_order_repo
        self._uow = uow

    async def handle(self, cmd: AssignOrderToWarehouseCommand) -> OrderAllocationResult:
        """Manually assign an order to a specific warehouse."""
        order = await self._sales_order_repo.get_by_id(cmd.order_id, cmd.tenant_id)
        if not order:
            raise ValueError(f"Order {cmd.order_id} not found")

        # Assign the warehouse
        old_warehouse_id = order.assigned_warehouse_id
        order.assigned_warehouse_id = cmd.warehouse_id
        order.assigned_at = datetime.now(timezone.utc)

        await self._sales_order_repo.save(order)
        await self._uow.commit()

        return OrderAllocationResult(
            order_id=str(cmd.order_id),
            allocated_warehouse_id=str(cmd.warehouse_id),
            status="allocated",
            message=f"Order manually assigned to warehouse {cmd.warehouse_id}" + 
                   (f" (was {old_warehouse_id})" if old_warehouse_id else ""),
        )


class ReassignOrderToWarehouseCommandHandler:
    """Handler for ReassignOrderToWarehouseCommand - Reassign to different warehouse."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        uow: SQLAlchemyUnitOfWork,
    ) -> None:
        self._sales_order_repo = sales_order_repo
        self._uow = uow

    async def handle(self, cmd: ReassignOrderToWarehouseCommand) -> OrderAllocationResult:
        """Reassign an order to a different warehouse."""
        order = await self._sales_order_repo.get_by_id(cmd.order_id, cmd.tenant_id)
        if not order:
            raise ValueError(f"Order {cmd.order_id} not found")

        old_warehouse_id = order.assigned_warehouse_id

        # Reassign
        order.assigned_warehouse_id = cmd.new_warehouse_id
        order.assigned_at = datetime.now(timezone.utc)

        await self._sales_order_repo.save(order)
        await self._uow.commit()

        return OrderAllocationResult(
            order_id=str(cmd.order_id),
            allocated_warehouse_id=str(cmd.new_warehouse_id),
            status="reassigned",
            message=f"Order reassigned from {old_warehouse_id} to {cmd.new_warehouse_id} (reason: {cmd.reason})",
        )


class ReleaseOrderFromWarehouseCommandHandler:
    """Handler for ReleaseOrderFromWarehouseCommand - Remove warehouse assignment."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        uow: SQLAlchemyUnitOfWork,
    ) -> None:
        self._sales_order_repo = sales_order_repo
        self._uow = uow

    async def handle(self, cmd: ReleaseOrderFromWarehouseCommand) -> OrderAllocationResult:
        """Release an order from its warehouse (undo allocation)."""
        order = await self._sales_order_repo.get_by_id(cmd.order_id, cmd.tenant_id)
        if not order:
            raise ValueError(f"Order {cmd.order_id} not found")

        old_warehouse_id = order.assigned_warehouse_id

        # Release
        order.assigned_warehouse_id = None
        order.assigned_at = None

        await self._sales_order_repo.save(order)
        await self._uow.commit()

        reason_msg = f" (reason: {cmd.reason})" if cmd.reason else ""
        return OrderAllocationResult(
            order_id=str(cmd.order_id),
            allocated_warehouse_id="",
            status="released",
            message=f"Order released from warehouse {old_warehouse_id}{reason_msg}",
        )
