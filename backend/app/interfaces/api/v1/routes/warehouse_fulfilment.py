"""Warehouse Fulfilment API routes.

Implements the full fulfilment cycle for Warehouse_User role:
accept, pick, pack, dispatch orders assigned to their warehouse.

RBAC: Restricted to Warehouse_User role with warehouse:fulfilment permission.
Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 6.5, 6.6, 6.7, 6.8, 6.9, 6.14
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.application.warehouse.commands import AcceptOrderCommand
from backend.app.application.warehouse.command_handlers import (
    AcceptOrderCommandHandler,
)
from backend.app.application.warehouse.pick_list_service import PickListService
from backend.app.domain.sales.repositories.sales_order_repository import (
    SalesOrderRepository,
)
from backend.app.domain.sales.services.order_state_machine import (
    InvalidTransitionError,
    OrderStateMachine,
)
from backend.app.domain.sales.value_objects.order_status import OrderStatus
from backend.app.infrastructure.persistence.models.pick_list_model import (
    PickListLineModel,
    PickListModel,
)
from backend.app.infrastructure.persistence.models.sales_models import (
    SalesOrderModel,
)
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_tenant_id,
    get_current_user_id,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission


router = APIRouter(prefix="/warehouse", tags=["Warehouse Fulfilment"])


# ── Request/Response Schemas ──────────────────────────────────────────────────


class PickItemRequest(BaseModel):
    """Request body for marking an item as picked."""

    pick_list_line_id: uuid.UUID = Field(
        ..., description="ID of the pick list line to mark as picked"
    )
    scanned_barcode: Optional[str] = Field(
        None,
        description="Barcode scanned during picking (optional barcode verification).",
    )


class PickListLineResponse(BaseModel):
    """Response schema for a pick list line item."""

    id: str
    order_line_id: str
    product_id: str
    product_name: str
    sku: str
    quantity: int
    storage_location: Optional[str] = None
    is_picked: bool
    picked_at: Optional[str] = None


class PickListResponse(BaseModel):
    """Response schema for a pick list."""

    id: str
    order_id: str
    warehouse_id: str
    status: str
    total_items: int
    picked_items: int
    lines: list[PickListLineResponse]
    created_at: str
    completed_at: Optional[str] = None


class OrderSummaryResponse(BaseModel):
    """Summary response for orders in the fulfilment workflow."""

    id: str
    order_number: str
    client_name: Optional[str] = None
    status: str
    grand_total: str
    assigned_at: Optional[str] = None
    accepted_at: Optional[str] = None
    item_count: int


class MyOrdersResponse(BaseModel):
    """Response for my-orders endpoint."""

    warehouse_id: str
    warehouse_name: str
    orders: list[OrderSummaryResponse]
    total: int


class DispatchQueueItem(BaseModel):
    """Response schema for a dispatch queue item."""

    id: str
    order_number: str
    client_name: Optional[str] = None
    status: str
    grand_total: str
    assigned_at: Optional[str] = None
    accepted_at: Optional[str] = None


class DispatchQueueResponse(BaseModel):
    """Response for dispatch-queue endpoint."""

    warehouse_id: str
    warehouse_name: str
    orders: list[DispatchQueueItem]
    total: int


# ── Internal Helpers ──────────────────────────────────────────────────────────


async def _get_user_warehouse(
    session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[uuid.UUID, str]:
    """Get the warehouse assigned to the current user.

    Returns (warehouse_id, warehouse_name) tuple.
    Raises HTTPException 403 if user has no warehouse assignment.
    """
    from backend.app.infrastructure.persistence.models.warehouse_model import (
        WarehouseModel,
        WarehouseUserAssignmentModel,
    )

    stmt = (
        select(WarehouseUserAssignmentModel, WarehouseModel)
        .join(
            WarehouseModel,
            WarehouseModel.id == WarehouseUserAssignmentModel.warehouse_id,
        )
        .where(
            WarehouseUserAssignmentModel.tenant_id == tenant_id,
            WarehouseUserAssignmentModel.user_id == user_id,
            WarehouseUserAssignmentModel.is_deleted == False,  # noqa: E712
            WarehouseModel.is_deleted == False,  # noqa: E712
        )
    )
    result = await session.execute(stmt)
    row = result.first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to any warehouse. Contact an administrator.",
        )
    assignment, warehouse = row
    return warehouse.id, warehouse.name


async def _get_order_for_warehouse(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    order_id: uuid.UUID,
    warehouse_id: uuid.UUID,
):
    """Fetch an order and verify it belongs to the user's warehouse.

    Returns the SalesOrder domain entity.
    Raises HTTPException if not found or not assigned to the warehouse.
    """
    order_repo = SalesOrderRepository(session)
    order = await order_repo.get_by_id(id=order_id, tenant_id=tenant_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )
    if order.assigned_warehouse_id != warehouse_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Order {order_id} is not assigned to your warehouse",
        )
    return order


def _pick_list_to_response(pick_list) -> PickListResponse:
    """Convert a PickList domain entity to a PickListResponse."""
    lines = [
        PickListLineResponse(
            id=str(line.id),
            order_line_id=str(line.order_line_id),
            product_id=str(line.product_id),
            product_name=line.product_name,
            sku=line.sku,
            quantity=line.quantity,
            storage_location=line.storage_location,
            is_picked=line.is_picked,
            picked_at=line.picked_at.isoformat() if line.picked_at else None,
        )
        for line in pick_list.lines
    ]
    return PickListResponse(
        id=str(pick_list.id),
        order_id=str(pick_list.order_id),
        warehouse_id=str(pick_list.warehouse_id),
        status=pick_list.status.value,
        total_items=pick_list.total_items,
        picked_items=pick_list.picked_items,
        lines=lines,
        created_at=pick_list.created_at.isoformat(),
        completed_at=(
            pick_list.completed_at.isoformat() if pick_list.completed_at else None
        ),
    )


async def _update_pick_list_in_db(session: AsyncSession, pick_list) -> None:
    """Update pick list and its lines in the database."""
    # Update pick list status
    await session.execute(
        sql_update(PickListModel)
        .where(PickListModel.id == pick_list.id)
        .values(
            status=pick_list.status.value,
            completed_at=pick_list.completed_at,
            updated_at=datetime.now(timezone.utc),
        )
    )

    # Update each line that has been picked
    for line in pick_list.lines:
        if line.is_picked:
            await session.execute(
                sql_update(PickListLineModel)
                .where(PickListLineModel.id == line.id)
                .values(
                    is_picked=True,
                    picked_at=line.picked_at,
                    updated_at=datetime.now(timezone.utc),
                )
            )


# ── GET /api/v1/warehouse/my-orders ──────────────────────────────────────────


@router.get(
    "/my-orders",
    response_model=MyOrdersResponse,
    summary="Get pending orders for current user's warehouse",
    dependencies=[Depends(require_permission("warehouse:fulfilment"))],
)
async def get_my_orders(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get orders assigned to current user's warehouse, sorted by assignment date asc."""
    container = get_container(request)
    async with container.session_factory() as session:
        warehouse_id, warehouse_name = await _get_user_warehouse(
            session, tenant_id, user_id
        )

        # Active fulfilment statuses
        active_statuses = [
            OrderStatus.ASSIGNED.value,
            OrderStatus.ACCEPTED.value,
            OrderStatus.PICKING.value,
            OrderStatus.PACKING.value,
            OrderStatus.READY_FOR_DISPATCH.value,
        ]
        stmt = (
            select(SalesOrderModel)
            .options(selectinload(SalesOrderModel.client))
            .where(
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.assigned_warehouse_id == warehouse_id,
                SalesOrderModel.status.in_(active_statuses),
                SalesOrderModel.is_deleted == False,  # noqa: E712
            )
            .order_by(SalesOrderModel.assigned_at.asc())
        )
        result = await session.execute(stmt)
        models = result.scalars().all()

        orders = [
            OrderSummaryResponse(
                id=str(m.id),
                order_number=m.order_number,
                client_name=m.client.name if m.client else None,
                status=m.status,
                grand_total=str(m.grand_total),
                assigned_at=m.assigned_at.isoformat() if m.assigned_at else None,
                accepted_at=m.accepted_at.isoformat() if m.accepted_at else None,
                item_count=len(m.lines) if m.lines else 0,
            )
            for m in models
        ]

    return MyOrdersResponse(
        warehouse_id=str(warehouse_id),
        warehouse_name=warehouse_name,
        orders=orders,
        total=len(orders),
    )


# ── POST /api/v1/warehouse/orders/{id}/accept ────────────────────────────────


@router.post(
    "/orders/{order_id}/accept",
    response_model=PickListResponse,
    summary="Accept an order and generate pick list",
    dependencies=[Depends(require_permission("warehouse:fulfilment"))],
)
async def accept_order(
    order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Accept an order (ASSIGNED → ACCEPTED) and generate pick list."""
    container = get_container(request)
    async with container.session_factory() as session:
        warehouse_id, _ = await _get_user_warehouse(session, tenant_id, user_id)
        order_repo = SalesOrderRepository(session)
        pick_list_service = PickListService(session)
        uow = SQLAlchemyUnitOfWork(
            session=session, event_dispatcher=container.event_dispatcher
        )

        handler = AcceptOrderCommandHandler(
            sales_order_repo=order_repo,
            pick_list_service=pick_list_service,
            uow=uow,
            audit_service=getattr(container, "audit_service", None),
        )

        try:
            pick_list = await handler.handle(
                AcceptOrderCommand(
                    tenant_id=tenant_id,
                    order_id=order_id,
                    warehouse_id=warehouse_id,
                    accepted_by=user_id,
                )
            )
        except InvalidTransitionError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            )
        except ValueError as e:
            msg = str(e)
            if "not found" in msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=msg
                )
            if "not assigned" in msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail=msg
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=msg
            )

    return _pick_list_to_response(pick_list)


# ── POST /api/v1/warehouse/orders/{id}/decline ───────────────────────────────


@router.post(
    "/orders/{order_id}/decline",
    status_code=status.HTTP_200_OK,
    summary="Decline an order (ASSIGNED → PENDING_MANUAL_ASSIGNMENT)",
    dependencies=[Depends(require_permission("warehouse:fulfilment"))],
)
async def decline_order(
    order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Decline an order assigned to user's warehouse. Notifies Admin."""
    container = get_container(request)
    async with container.session_factory() as session:
        warehouse_id, _ = await _get_user_warehouse(session, tenant_id, user_id)
        order = await _get_order_for_warehouse(
            session, tenant_id, order_id, warehouse_id
        )

        # Validate transition via state machine
        state_machine = OrderStateMachine(
            audit_service=getattr(container, "audit_service", None)
        )
        try:
            await state_machine.execute_transition(
                order=order,
                target_status=OrderStatus.PENDING_MANUAL_ASSIGNMENT,
                acting_user_id=user_id,
            )
        except InvalidTransitionError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            )

        # Clear warehouse assignment
        order.assigned_warehouse_id = None
        order.assigned_at = None

        # Persist changes
        order_repo = SalesOrderRepository(session)
        await order_repo.save(order)
        uow = SQLAlchemyUnitOfWork(
            session=session, event_dispatcher=container.event_dispatcher
        )
        await uow.commit()

    return {
        "detail": "Order declined. Admin has been notified for manual assignment."
    }


# ── GET /api/v1/warehouse/orders/{id}/pick-list ──────────────────────────────


@router.get(
    "/orders/{order_id}/pick-list",
    response_model=PickListResponse,
    summary="Get pick list for an accepted order",
    dependencies=[Depends(require_permission("warehouse:fulfilment"))],
)
async def get_pick_list(
    order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get pick list for an order that has been accepted."""
    container = get_container(request)
    async with container.session_factory() as session:
        warehouse_id, _ = await _get_user_warehouse(session, tenant_id, user_id)

        # Verify order belongs to user's warehouse
        await _get_order_for_warehouse(session, tenant_id, order_id, warehouse_id)

        # Fetch pick list
        pick_list_service = PickListService(session)
        pick_list = await pick_list_service.get_pick_list_by_order(
            tenant_id=tenant_id, order_id=order_id
        )
        if pick_list is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"No pick list found for order {order_id}. "
                    "The order may not have been accepted yet."
                ),
            )

    return _pick_list_to_response(pick_list)


# ── POST /api/v1/warehouse/orders/{id}/pick-item ─────────────────────────────


@router.post(
    "/orders/{order_id}/pick-item",
    response_model=PickListResponse,
    summary="Mark item as picked, update pick progress",
    dependencies=[Depends(require_permission("warehouse:fulfilment"))],
)
async def pick_item(
    order_id: uuid.UUID,
    body: PickItemRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Mark an item as picked. Updates pick progress (picked count vs total).

    If scanned_barcode is provided, validates against expected product barcode.
    """
    container = get_container(request)
    async with container.session_factory() as session:
        warehouse_id, _ = await _get_user_warehouse(session, tenant_id, user_id)
        order = await _get_order_for_warehouse(
            session, tenant_id, order_id, warehouse_id
        )

        # Order must be in ACCEPTED or PICKING status
        if order.status not in (OrderStatus.ACCEPTED, OrderStatus.PICKING):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Cannot pick items for order in {order.status.value} status. "
                    "Order must be in ACCEPTED or PICKING status."
                ),
            )

        # Fetch the pick list
        pick_list_service = PickListService(session)
        pick_list = await pick_list_service.get_pick_list_by_order(
            tenant_id=tenant_id, order_id=order_id
        )
        if pick_list is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No pick list found for order {order_id}.",
            )

        # Barcode verification if provided (Req 7.7, 7.8)
        if body.scanned_barcode:
            await _verify_barcode(
                session=session,
                tenant_id=tenant_id,
                pick_list=pick_list,
                line_id=body.pick_list_line_id,
                scanned_barcode=body.scanned_barcode,
            )

        # Mark the item as picked (domain validates line exists & not already picked)
        try:
            pick_list.mark_item_picked(body.pick_list_line_id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            )

        # If order is in ACCEPTED, transition to PICKING on first pick
        if order.status == OrderStatus.ACCEPTED:
            state_machine = OrderStateMachine(
                audit_service=getattr(container, "audit_service", None)
            )
            await state_machine.execute_transition(
                order=order,
                target_status=OrderStatus.PICKING,
                acting_user_id=user_id,
            )
            order_repo = SalesOrderRepository(session)
            await order_repo.save(order)

        # Persist pick list changes
        await _update_pick_list_in_db(session, pick_list)
        uow = SQLAlchemyUnitOfWork(
            session=session, event_dispatcher=container.event_dispatcher
        )
        await uow.commit()

    return _pick_list_to_response(pick_list)


# ── POST /api/v1/warehouse/orders/{id}/start-packing ─────────────────────────


@router.post(
    "/orders/{order_id}/start-packing",
    status_code=status.HTTP_200_OK,
    summary="Transition PICKING → PACKING (all items must be picked)",
    dependencies=[Depends(require_permission("warehouse:fulfilment"))],
)
async def start_packing(
    order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Transition order to PACKING. Only allowed when all pick list items are picked."""
    container = get_container(request)
    async with container.session_factory() as session:
        warehouse_id, _ = await _get_user_warehouse(session, tenant_id, user_id)
        order = await _get_order_for_warehouse(
            session, tenant_id, order_id, warehouse_id
        )

        # Verify all items are picked
        pick_list_service = PickListService(session)
        pick_list = await pick_list_service.get_pick_list_by_order(
            tenant_id=tenant_id, order_id=order_id
        )
        if pick_list is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No pick list found for this order.",
            )
        if not pick_list.is_fully_picked:
            remaining = pick_list.total_items - pick_list.picked_items
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Cannot start packing: {remaining} item(s) remain unpicked. "
                    f"Picked {pick_list.picked_items}/{pick_list.total_items}."
                ),
            )

        # Transition via state machine
        state_machine = OrderStateMachine(
            audit_service=getattr(container, "audit_service", None)
        )
        try:
            await state_machine.execute_transition(
                order=order,
                target_status=OrderStatus.PACKING,
                acting_user_id=user_id,
            )
        except InvalidTransitionError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            )

        # Persist
        order_repo = SalesOrderRepository(session)
        await order_repo.save(order)
        uow = SQLAlchemyUnitOfWork(
            session=session, event_dispatcher=container.event_dispatcher
        )
        await uow.commit()

    return {
        "detail": "Order transitioned to PACKING.",
        "status": OrderStatus.PACKING.value,
    }


# ── POST /api/v1/warehouse/orders/{id}/complete-packing ──────────────────────


@router.post(
    "/orders/{order_id}/complete-packing",
    status_code=status.HTTP_200_OK,
    summary="Transition PACKING → READY_FOR_DISPATCH",
    dependencies=[Depends(require_permission("warehouse:fulfilment"))],
)
async def complete_packing(
    order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Complete packing and add order to dispatch queue."""
    container = get_container(request)
    async with container.session_factory() as session:
        warehouse_id, _ = await _get_user_warehouse(session, tenant_id, user_id)
        order = await _get_order_for_warehouse(
            session, tenant_id, order_id, warehouse_id
        )

        # Transition via state machine
        state_machine = OrderStateMachine(
            audit_service=getattr(container, "audit_service", None)
        )
        try:
            await state_machine.execute_transition(
                order=order,
                target_status=OrderStatus.READY_FOR_DISPATCH,
                acting_user_id=user_id,
            )
        except InvalidTransitionError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            )

        # Persist
        order_repo = SalesOrderRepository(session)
        await order_repo.save(order)
        uow = SQLAlchemyUnitOfWork(
            session=session, event_dispatcher=container.event_dispatcher
        )
        await uow.commit()

    return {
        "detail": "Order packing complete. Added to dispatch queue.",
        "status": OrderStatus.READY_FOR_DISPATCH.value,
    }


# ── POST /api/v1/warehouse/orders/{id}/dispatch ──────────────────────────────


@router.post(
    "/orders/{order_id}/dispatch",
    status_code=status.HTTP_200_OK,
    summary="Dispatch order (READY_FOR_DISPATCH → DISPATCHED)",
    dependencies=[Depends(require_permission("warehouse:fulfilment"))],
)
async def dispatch_order(
    order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Dispatch the order."""
    container = get_container(request)
    async with container.session_factory() as session:
        warehouse_id, _ = await _get_user_warehouse(session, tenant_id, user_id)
        order = await _get_order_for_warehouse(
            session, tenant_id, order_id, warehouse_id
        )

        # Transition via state machine
        state_machine = OrderStateMachine(
            audit_service=getattr(container, "audit_service", None)
        )
        try:
            await state_machine.execute_transition(
                order=order,
                target_status=OrderStatus.DISPATCHED,
                acting_user_id=user_id,
            )
        except InvalidTransitionError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            )

        # Persist
        order_repo = SalesOrderRepository(session)
        await order_repo.save(order)
        uow = SQLAlchemyUnitOfWork(
            session=session, event_dispatcher=container.event_dispatcher
        )
        await uow.commit()

    return {"detail": "Order dispatched.", "status": OrderStatus.DISPATCHED.value}


# ── GET /api/v1/warehouse/dispatch-queue ─────────────────────────────────────


@router.get(
    "/dispatch-queue",
    response_model=DispatchQueueResponse,
    summary="View dispatch queue for user's warehouse",
    dependencies=[Depends(require_permission("warehouse:fulfilment"))],
)
async def get_dispatch_queue(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """View orders in READY_FOR_DISPATCH status for user's warehouse."""
    container = get_container(request)
    async with container.session_factory() as session:
        warehouse_id, warehouse_name = await _get_user_warehouse(
            session, tenant_id, user_id
        )

        stmt = (
            select(SalesOrderModel)
            .options(selectinload(SalesOrderModel.client))
            .where(
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.assigned_warehouse_id == warehouse_id,
                SalesOrderModel.status == OrderStatus.READY_FOR_DISPATCH.value,
                SalesOrderModel.is_deleted == False,  # noqa: E712
            )
            .order_by(SalesOrderModel.assigned_at.asc())
        )
        result = await session.execute(stmt)
        models = result.scalars().all()

        orders = [
            DispatchQueueItem(
                id=str(m.id),
                order_number=m.order_number,
                client_name=m.client.name if m.client else None,
                status=m.status,
                grand_total=str(m.grand_total),
                assigned_at=m.assigned_at.isoformat() if m.assigned_at else None,
                accepted_at=m.accepted_at.isoformat() if m.accepted_at else None,
            )
            for m in models
        ]

    return DispatchQueueResponse(
        warehouse_id=str(warehouse_id),
        warehouse_name=warehouse_name,
        orders=orders,
        total=len(orders),
    )


# ── Barcode Verification Helper ──────────────────────────────────────────────


async def _verify_barcode(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    pick_list,
    line_id: uuid.UUID,
    scanned_barcode: str,
) -> None:
    """Verify scanned barcode matches expected product barcode.

    If barcode scanning is enabled (scanned_barcode is provided) and the
    scanned value doesn't match the expected product barcode, raises HTTP 422.

    Requirements: 7.7, 7.8
    """
    from backend.app.infrastructure.persistence.models.material_model import (
        MaterialModel,
    )

    # Find the target line
    target_line = next(
        (line for line in pick_list.lines if line.id == line_id), None
    )
    if target_line is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pick list line {line_id} not found",
        )

    # Look up the expected product barcode from the material record
    stmt = select(MaterialModel.barcode, MaterialModel.name).where(
        MaterialModel.id == target_line.product_id,
        MaterialModel.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    row = result.one_or_none()

    if row is None:
        return  # Product not found — skip barcode verification

    expected_barcode = row[0]
    product_name = row[1] or target_line.product_name

    # If the product has no barcode configured, skip verification
    if not expected_barcode:
        return

    # Compare scanned barcode to expected barcode
    if scanned_barcode.strip() != expected_barcode.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Barcode mismatch: scanned barcode does not match expected "
                f"product barcode. Expected product: {product_name}, "
                f"expected barcode: {expected_barcode}, "
                f"scanned: {scanned_barcode}"
            ),
        )
