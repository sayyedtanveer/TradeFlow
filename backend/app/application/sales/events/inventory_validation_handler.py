"""Inventory Validation Event Handler.

Listens for `order.placed` events and validates stock availability across warehouses.

Workflow:
1. Fetch the order and all active warehouses for the tenant.
2. For each warehouse, check if it can fulfill ALL line items (available_stock >= quantity).
3. If a single warehouse can fulfill: reserve stock, assign the order, transition to ASSIGNED,
   notify warehouse users.
4. If no single warehouse can fulfill but total stock across all warehouses is sufficient:
   transition to PENDING_MANUAL_ASSIGNMENT, notify Admin.
5. If total stock is insufficient for any line item: transition to CANCELLED,
   release reservations, notify Client with shortage details.

Requirements: 6.1, 6.2, 6.3, 6.4
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.application.sales.events.order_placed_event import OrderPlacedEvent
from backend.app.application.inventory.services.stock_service import InventoryService
from backend.app.domain.sales.entities.sales_order import SalesOrder
from backend.app.domain.sales.services.order_state_machine import OrderStateMachine
from backend.app.domain.sales.value_objects.order_status import OrderStatus
from backend.app.domain.shared.domain_event import DomainEvent
from backend.app.infrastructure.events.event_handler_interface import IEventHandler
from backend.app.infrastructure.websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


class InventoryValidationHandler(IEventHandler[OrderPlacedEvent]):
    """
    Event handler that validates inventory availability when an order is placed.

    Subscribes to: order.placed
    Executes within 5 seconds of order placement (in-process, sync with event bus).

    Dependencies (injected at construction):
    - session_factory: SQLAlchemy async session factory for DB access
    - connection_manager: WebSocket manager for real-time notifications
    - audit_service: For recording state transitions in audit trail
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        connection_manager: ConnectionManager,
        audit_service=None,
    ) -> None:
        self._session_factory = session_factory
        self._connection_manager = connection_manager
        self._audit_service = audit_service

    @property
    def event_type(self) -> str:
        return "order.placed"

    async def handle(self, event: DomainEvent) -> None:
        """Process the order.placed event by validating inventory."""
        try:
            await self._validate_inventory(event)
        except Exception as e:
            logger.error(
                "Inventory validation failed for order %s: %s",
                getattr(event, "order_id", event.aggregate_id),
                str(e),
                exc_info=True,
            )

    async def _validate_inventory(self, event: DomainEvent) -> None:
        """Core inventory validation logic."""
        order_id = getattr(event, "order_id", event.aggregate_id)
        tenant_id = event.tenant_id
        order_number = getattr(event, "order_number", "")
        client_id = getattr(event, "client_id", None)
        lines = getattr(event, "lines", [])

        if not lines:
            logger.warning("Order %s has no line items, skipping validation", order_id)
            return

        async with self._session_factory() as session:
            async with session.begin():
                inventory_service = InventoryService(session)

                # Get all active warehouses for this tenant
                warehouses = await self._get_active_warehouses(session, tenant_id)

                if not warehouses:
                    # No warehouses configured — cancel the order
                    await self._cancel_order(
                        session=session,
                        inventory_service=inventory_service,
                        tenant_id=tenant_id,
                        order_id=order_id,
                        order_number=order_number,
                        client_id=client_id,
                        shortage_details=[
                            {
                                "product_id": str(line.product_id),
                                "requested": line.quantity,
                                "available": 0,
                                "reason": "No active warehouses configured",
                            }
                            for line in lines
                        ],
                    )
                    return

                # Step 1: Find a single warehouse that can fulfill ALL items
                optimal_warehouse = await self._find_optimal_warehouse(
                    inventory_service=inventory_service,
                    tenant_id=tenant_id,
                    warehouses=warehouses,
                    lines=lines,
                )

                if optimal_warehouse is not None:
                    # SUCCESS: Single warehouse can fulfill the entire order
                    await self._assign_to_warehouse(
                        session=session,
                        inventory_service=inventory_service,
                        tenant_id=tenant_id,
                        order_id=order_id,
                        order_number=order_number,
                        warehouse_id=optimal_warehouse["id"],
                        warehouse_name=optimal_warehouse["name"],
                        lines=lines,
                    )
                    return

                # Step 2: Check if total stock across all warehouses is sufficient
                shortage_details = await self._check_total_availability(
                    inventory_service=inventory_service,
                    tenant_id=tenant_id,
                    warehouses=warehouses,
                    lines=lines,
                )

                if shortage_details:
                    # FAILURE: Insufficient total stock — cancel order
                    await self._cancel_order(
                        session=session,
                        inventory_service=inventory_service,
                        tenant_id=tenant_id,
                        order_id=order_id,
                        order_number=order_number,
                        client_id=client_id,
                        shortage_details=shortage_details,
                    )
                else:
                    # PARTIAL: Stock exists but spread across warehouses
                    await self._mark_pending_manual_assignment(
                        session=session,
                        tenant_id=tenant_id,
                        order_id=order_id,
                        order_number=order_number,
                    )

    async def _get_active_warehouses(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> list[dict]:
        """Fetch all active warehouses for the tenant."""
        from sqlalchemy import select
        from backend.app.infrastructure.persistence.models.warehouse_model import WarehouseModel

        stmt = (
            select(WarehouseModel)
            .where(
                WarehouseModel.tenant_id == tenant_id,
                WarehouseModel.is_active.is_(True),
                WarehouseModel.is_deleted.is_(False),
            )
        )
        result = await session.execute(stmt)
        warehouses = result.scalars().all()
        return [{"id": w.id, "name": w.name} for w in warehouses]

    async def _resolve_material_id(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        product_type: str,
    ) -> Optional[uuid.UUID]:
        """Resolve a sellable product to its inventory material_id."""
        from sqlalchemy import select
        from backend.app.infrastructure.persistence.models.material_model import MaterialModel
        from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel

        # Try direct material lookup
        direct = await session.execute(
            select(MaterialModel.id).where(
                MaterialModel.id == product_id,
                MaterialModel.tenant_id == tenant_id,
                MaterialModel.is_deleted.is_(False),
            )
        )
        material_id = direct.scalar_one_or_none()
        if material_id is not None:
            return material_id

        # Try variant → material mapping
        if product_type == "variant":
            variant_result = await session.execute(
                select(ItemVariantModel).where(
                    ItemVariantModel.id == product_id,
                    ItemVariantModel.tenant_id == tenant_id,
                    ItemVariantModel.is_deleted.is_(False),
                )
            )
            variant = variant_result.scalar_one_or_none()
            if variant is not None:
                if getattr(variant, "material_id", None):
                    return variant.material_id
                # Fallback: match by code
                material_by_code = await session.execute(
                    select(MaterialModel.id).where(
                        MaterialModel.tenant_id == tenant_id,
                        MaterialModel.code == variant.code,
                        MaterialModel.material_type == "finished",
                        MaterialModel.is_deleted.is_(False),
                    )
                )
                return material_by_code.scalar_one_or_none()

        return None

    async def _find_optimal_warehouse(
        self,
        inventory_service: InventoryService,
        tenant_id: uuid.UUID,
        warehouses: list[dict],
        lines: list,
    ) -> Optional[dict]:
        """
        Find the optimal warehouse that can fulfill all order line items.

        Strategy: find the first warehouse that has sufficient available stock
        for every line item. Warehouses are evaluated in order (could be enhanced
        with proximity-based optimization in future).

        Returns:
            Warehouse dict if found, None otherwise.
        """
        session = inventory_service._session

        for warehouse in warehouses:
            warehouse_id = warehouse["id"]
            can_fulfill_all = True

            for line in lines:
                material_id = await self._resolve_material_id(
                    session, tenant_id, line.product_id, line.product_type
                )
                if material_id is None:
                    can_fulfill_all = False
                    break

                available = await inventory_service.get_available_stock_for_warehouse(
                    tenant_id=tenant_id,
                    material_id=material_id,
                    warehouse_id=warehouse_id,
                )

                if available < Decimal(str(line.quantity)):
                    can_fulfill_all = False
                    break

            if can_fulfill_all:
                return warehouse

        return None

    async def _check_total_availability(
        self,
        inventory_service: InventoryService,
        tenant_id: uuid.UUID,
        warehouses: list[dict],
        lines: list,
    ) -> list[dict]:
        """
        Check if total stock across all warehouses is sufficient for each line item.

        Returns:
            List of shortage details (empty if total stock is sufficient).
        """
        session = inventory_service._session
        shortage_details = []

        for line in lines:
            material_id = await self._resolve_material_id(
                session, tenant_id, line.product_id, line.product_type
            )
            if material_id is None:
                shortage_details.append({
                    "product_id": str(line.product_id),
                    "requested": line.quantity,
                    "available": 0,
                    "reason": "Product not found in inventory",
                })
                continue

            # Sum available stock across all warehouses
            total_available = Decimal("0")
            for warehouse in warehouses:
                available = await inventory_service.get_available_stock_for_warehouse(
                    tenant_id=tenant_id,
                    material_id=material_id,
                    warehouse_id=warehouse["id"],
                )
                total_available += available

            requested = Decimal(str(line.quantity))
            if total_available < requested:
                shortage_details.append({
                    "product_id": str(line.product_id),
                    "requested": float(requested),
                    "available": float(total_available),
                    "reason": "Insufficient stock across all warehouses",
                })

        return shortage_details

    async def _assign_to_warehouse(
        self,
        session: AsyncSession,
        inventory_service: InventoryService,
        tenant_id: uuid.UUID,
        order_id: uuid.UUID,
        order_number: str,
        warehouse_id: uuid.UUID,
        warehouse_name: str,
        lines: list,
    ) -> None:
        """
        Assign the order to the optimal warehouse.

        Steps:
        1. Reserve stock in the warehouse for all line items
        2. Update order: set assigned_warehouse_id, transition to ASSIGNED
        3. Notify warehouse users
        """
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from backend.app.infrastructure.persistence.models.sales_models import SalesOrderModel

        # Reserve stock for each line item in the assigned warehouse
        system_user_id = uuid.UUID(int=0)
        for line in lines:
            material_id = await self._resolve_material_id(
                session, tenant_id, line.product_id, line.product_type
            )
            if material_id is None:
                continue

            await inventory_service.reserve_sales_stock(
                tenant_id=tenant_id,
                material_id=material_id,
                quantity=Decimal(str(line.quantity)),
                sales_order_line_id=line.line_id,
                unit_id=line.uom_id,
                created_by=system_user_id,
                warehouse_id=warehouse_id,
                order_id=order_id,
            )

        # Update order status to ASSIGNED and set warehouse
        stmt = (
            select(SalesOrderModel)
            .options(selectinload(SalesOrderModel.lines))
            .where(
                SalesOrderModel.id == order_id,
                SalesOrderModel.tenant_id == tenant_id,
            )
            .with_for_update()
        )
        result = await session.execute(stmt)
        order_model = result.scalar_one_or_none()

        if order_model is None:
            logger.error("Order %s not found during warehouse assignment", order_id)
            return

        order_model.status = OrderStatus.ASSIGNED.value
        order_model.assigned_warehouse_id = warehouse_id
        order_model.assigned_at = datetime.now(timezone.utc)

        # Record audit log for the transition
        if self._audit_service:
            await self._audit_service.log_action(
                action="ORDER_STATUS_TRANSITION",
                entity_type="sales_order",
                entity_id=order_id,
                before_value={"status": OrderStatus.PENDING_INVENTORY_VALIDATION.value},
                after_value={"status": OrderStatus.ASSIGNED.value},
                extra={
                    "source": "inventory_validation_handler",
                    "module": "sales",
                    "summary": (
                        f"Order auto-assigned to warehouse '{warehouse_name}' "
                        f"after successful inventory validation"
                    ),
                    "previous_status": OrderStatus.PENDING_INVENTORY_VALIDATION.value,
                    "new_status": OrderStatus.ASSIGNED.value,
                    "warehouse_id": str(warehouse_id),
                    "warehouse_name": warehouse_name,
                    "transition_timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        # Notify warehouse users via WebSocket
        await self._notify_warehouse_users(
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
            order_id=order_id,
            order_number=order_number,
        )

        logger.info(
            "Order %s assigned to warehouse %s (%s)",
            order_id, warehouse_id, warehouse_name,
        )

    async def _cancel_order(
        self,
        session: AsyncSession,
        inventory_service: InventoryService,
        tenant_id: uuid.UUID,
        order_id: uuid.UUID,
        order_number: str,
        client_id: Optional[uuid.UUID],
        shortage_details: list[dict],
    ) -> None:
        """
        Cancel the order due to insufficient inventory.

        Steps:
        1. Release any existing reservations for this order
        2. Transition order to CANCELLED
        3. Notify client with shortage details
        """
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from backend.app.infrastructure.persistence.models.sales_models import SalesOrderModel

        # Release any reservations that may have been created
        system_user_id = uuid.UUID(int=0)
        await inventory_service.release_all_reservations_for_order(
            tenant_id=tenant_id,
            order_id=order_id,
            created_by=system_user_id,
        )

        # Update order status to CANCELLED
        stmt = (
            select(SalesOrderModel)
            .options(selectinload(SalesOrderModel.lines))
            .where(
                SalesOrderModel.id == order_id,
                SalesOrderModel.tenant_id == tenant_id,
            )
            .with_for_update()
        )
        result = await session.execute(stmt)
        order_model = result.scalar_one_or_none()

        if order_model is None:
            logger.error("Order %s not found during cancellation", order_id)
            return

        order_model.status = OrderStatus.CANCELLED.value

        # Record audit log for the cancellation
        if self._audit_service:
            await self._audit_service.log_action(
                action="ORDER_STATUS_TRANSITION",
                entity_type="sales_order",
                entity_id=order_id,
                before_value={"status": OrderStatus.PENDING_INVENTORY_VALIDATION.value},
                after_value={"status": OrderStatus.CANCELLED.value},
                extra={
                    "source": "inventory_validation_handler",
                    "module": "sales",
                    "summary": (
                        f"Order cancelled due to insufficient inventory. "
                        f"Shortages: {shortage_details}"
                    ),
                    "previous_status": OrderStatus.PENDING_INVENTORY_VALIDATION.value,
                    "new_status": OrderStatus.CANCELLED.value,
                    "shortage_details": shortage_details,
                    "transition_timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        # Notify the client about the cancellation with shortage details
        await self._notify_client_cancellation(
            tenant_id=tenant_id,
            client_id=client_id,
            order_id=order_id,
            order_number=order_number,
            shortage_details=shortage_details,
        )

        logger.info(
            "Order %s cancelled due to insufficient inventory: %s",
            order_id, shortage_details,
        )

    async def _mark_pending_manual_assignment(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        order_id: uuid.UUID,
        order_number: str,
    ) -> None:
        """
        Transition order to PENDING_MANUAL_ASSIGNMENT when no single warehouse
        can fulfill but total stock is sufficient.

        Steps:
        1. Transition order to PENDING_MANUAL_ASSIGNMENT
        2. Notify Admin that manual assignment is required
        """
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from backend.app.infrastructure.persistence.models.sales_models import SalesOrderModel

        # Update order status
        stmt = (
            select(SalesOrderModel)
            .options(selectinload(SalesOrderModel.lines))
            .where(
                SalesOrderModel.id == order_id,
                SalesOrderModel.tenant_id == tenant_id,
            )
            .with_for_update()
        )
        result = await session.execute(stmt)
        order_model = result.scalar_one_or_none()

        if order_model is None:
            logger.error("Order %s not found during manual assignment", order_id)
            return

        order_model.status = OrderStatus.PENDING_MANUAL_ASSIGNMENT.value

        # Record audit log
        if self._audit_service:
            await self._audit_service.log_action(
                action="ORDER_STATUS_TRANSITION",
                entity_type="sales_order",
                entity_id=order_id,
                before_value={"status": OrderStatus.PENDING_INVENTORY_VALIDATION.value},
                after_value={"status": OrderStatus.PENDING_MANUAL_ASSIGNMENT.value},
                extra={
                    "source": "inventory_validation_handler",
                    "module": "sales",
                    "summary": (
                        "No single warehouse can fulfill all items. "
                        "Admin manual assignment required."
                    ),
                    "previous_status": OrderStatus.PENDING_INVENTORY_VALIDATION.value,
                    "new_status": OrderStatus.PENDING_MANUAL_ASSIGNMENT.value,
                    "transition_timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        # Notify Admin (broadcast to tenant — admins see all notifications)
        await self._notify_admin_manual_assignment(
            tenant_id=tenant_id,
            order_id=order_id,
            order_number=order_number,
        )

        logger.info(
            "Order %s moved to PENDING_MANUAL_ASSIGNMENT — no single warehouse can fulfill",
            order_id,
        )

    # ── Notification helpers ──────────────────────────────────────────────

    async def _notify_warehouse_users(
        self,
        tenant_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        order_id: uuid.UUID,
        order_number: str,
    ) -> None:
        """Send notification to all warehouse users about a newly assigned order."""
        notification = {
            "id": str(uuid.uuid4()),
            "type": "ORDER_ASSIGNED",
            "title": "New Order Assigned",
            "message": f"Order {order_number} has been assigned to your warehouse",
            "data": {
                "order_id": str(order_id),
                "order_number": order_number,
                "warehouse_id": str(warehouse_id),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "priority": "info",
        }

        # Broadcast to the entire tenant (warehouse users will filter client-side,
        # or the notification service can be enhanced later for role-based delivery)
        await self._connection_manager.broadcast_to_tenant(
            tenant_id=tenant_id,
            message_type="notification",
            payload=notification,
        )

    async def _notify_client_cancellation(
        self,
        tenant_id: uuid.UUID,
        client_id: Optional[uuid.UUID],
        order_id: uuid.UUID,
        order_number: str,
        shortage_details: list[dict],
    ) -> None:
        """Notify the client that their order was cancelled due to stock shortage."""
        notification = {
            "id": str(uuid.uuid4()),
            "type": "ORDER_CANCELLED",
            "title": "Order Cancelled",
            "message": (
                f"Order {order_number} has been cancelled due to insufficient stock"
            ),
            "data": {
                "order_id": str(order_id),
                "order_number": order_number,
                "reason": "insufficient_inventory",
                "shortage_details": shortage_details,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "priority": "error",
        }

        if client_id:
            await self._connection_manager.send_to_user(
                tenant_id=tenant_id,
                user_id=client_id,
                message_type="notification",
                payload=notification,
            )
        else:
            # Fallback: broadcast to tenant
            await self._connection_manager.broadcast_to_tenant(
                tenant_id=tenant_id,
                message_type="notification",
                payload=notification,
            )

    async def _notify_admin_manual_assignment(
        self,
        tenant_id: uuid.UUID,
        order_id: uuid.UUID,
        order_number: str,
    ) -> None:
        """Notify Admin that manual warehouse assignment is required."""
        notification = {
            "id": str(uuid.uuid4()),
            "type": "ORDER_NEEDS_MANUAL_ASSIGNMENT",
            "title": "Manual Assignment Required",
            "message": (
                f"Order {order_number} requires manual warehouse assignment — "
                f"no single warehouse can fulfill all items"
            ),
            "data": {
                "order_id": str(order_id),
                "order_number": order_number,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "priority": "warning",
        }

        # Broadcast to tenant (Admin users will see this)
        await self._connection_manager.broadcast_to_tenant(
            tenant_id=tenant_id,
            message_type="notification",
            payload=notification,
        )
