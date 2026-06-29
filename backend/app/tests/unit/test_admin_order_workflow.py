"""Unit tests for Admin Order Workflow command handlers.

Tests the 4 admin workflow operations:
- AssignWarehouseCommandHandler
- PlaceOrderOnHoldCommandHandler
- ReleaseOrderHoldCommandHandler
- AdminCancelOrderCommandHandler

Requirements validated: 6.13, 6.15, 6.16, 2.1
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.domain.sales.entities.sales_order import SalesOrder
from backend.app.domain.sales.value_objects.order_status import OrderStatus
from backend.app.domain.sales.services.order_state_machine import (
    InvalidTransitionError,
    OrderStateMachine,
)
from backend.app.application.sales.commands import (
    AssignWarehouseCommand,
    PlaceOrderOnHoldCommand,
    ReleaseOrderHoldCommand,
    AdminCancelOrderCommand,
)
from backend.app.application.sales.command_handlers import (
    AssignWarehouseCommandHandler,
    PlaceOrderOnHoldCommandHandler,
    ReleaseOrderHoldCommandHandler,
    AdminCancelOrderCommandHandler,
)


# ── Test Fixtures ────────────────────────────────────────────────────────────


def _make_order(
    *,
    status: OrderStatus = OrderStatus.PENDING_MANUAL_ASSIGNMENT,
    tenant_id: uuid.UUID | None = None,
    order_id: uuid.UUID | None = None,
) -> SalesOrder:
    """Create a minimal SalesOrder entity for testing."""
    return SalesOrder(
        id=order_id or uuid.uuid4(),
        tenant_id=tenant_id or uuid.uuid4(),
        order_number="SO-20260101-001",
        client_id=uuid.uuid4(),
        order_date=date(2026, 1, 1),
        delivery_date=date(2026, 1, 15),
        status=status,
    )


def _make_repo(order: SalesOrder) -> AsyncMock:
    """Create a mock SalesOrderRepository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=order)
    repo.save = AsyncMock()
    return repo


def _make_uow() -> AsyncMock:
    """Create a mock Unit of Work."""
    uow = AsyncMock()
    uow.work = AsyncMock()
    return uow


def _make_audit_service() -> AsyncMock:
    """Create a mock audit service."""
    audit = AsyncMock()
    audit.log_action = AsyncMock()
    return audit


def _make_inventory_service() -> AsyncMock:
    """Create a mock inventory service (for release_all_reservations_for_order)."""
    svc = AsyncMock()
    svc.release_all_reservations_for_order = AsyncMock()
    return svc


# ── AssignWarehouseCommandHandler Tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_assign_warehouse_success():
    """Assign warehouse to PENDING_MANUAL_ASSIGNMENT order transitions to ASSIGNED."""
    tenant_id = uuid.uuid4()
    order_id = uuid.uuid4()
    warehouse_id = uuid.uuid4()
    user_id = uuid.uuid4()

    order = _make_order(status=OrderStatus.PENDING_MANUAL_ASSIGNMENT, tenant_id=tenant_id, order_id=order_id)
    repo = _make_repo(order)
    uow = _make_uow()
    audit = _make_audit_service()

    handler = AssignWarehouseCommandHandler(repo, uow, audit_service=audit)
    command = AssignWarehouseCommand(
        tenant_id=tenant_id,
        sales_order_id=order_id,
        warehouse_id=warehouse_id,
        assigned_by=user_id,
    )

    await handler.handle(command)

    assert order.status == OrderStatus.ASSIGNED
    assert order.assigned_warehouse_id == warehouse_id
    assert order.assigned_at is not None
    repo.save.assert_awaited_once_with(order)
    uow.work.assert_awaited_once()
    audit.log_action.assert_awaited_once()


@pytest.mark.asyncio
async def test_assign_warehouse_invalid_state_raises():
    """Assigning warehouse to ASSIGNED order raises InvalidTransitionError."""
    tenant_id = uuid.uuid4()
    order_id = uuid.uuid4()

    order = _make_order(status=OrderStatus.ASSIGNED, tenant_id=tenant_id, order_id=order_id)
    repo = _make_repo(order)
    uow = _make_uow()

    handler = AssignWarehouseCommandHandler(repo, uow)
    command = AssignWarehouseCommand(
        tenant_id=tenant_id,
        sales_order_id=order_id,
        warehouse_id=uuid.uuid4(),
        assigned_by=uuid.uuid4(),
    )

    with pytest.raises(InvalidTransitionError) as exc_info:
        await handler.handle(command)

    assert exc_info.value.current_status == OrderStatus.ASSIGNED
    assert exc_info.value.target_status == OrderStatus.ASSIGNED


@pytest.mark.asyncio
async def test_assign_warehouse_order_not_found():
    """Raises ValueError when order does not exist."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    uow = _make_uow()

    handler = AssignWarehouseCommandHandler(repo, uow)
    command = AssignWarehouseCommand(
        tenant_id=uuid.uuid4(),
        sales_order_id=uuid.uuid4(),
        warehouse_id=uuid.uuid4(),
        assigned_by=uuid.uuid4(),
    )

    with pytest.raises(ValueError, match="not found"):
        await handler.handle(command)


# ── PlaceOrderOnHoldCommandHandler Tests ─────────────────────────────────────


@pytest.mark.asyncio
async def test_hold_order_from_assigned():
    """Place ASSIGNED order on hold transitions to ON_HOLD."""
    tenant_id = uuid.uuid4()
    order_id = uuid.uuid4()

    order = _make_order(status=OrderStatus.ASSIGNED, tenant_id=tenant_id, order_id=order_id)
    repo = _make_repo(order)
    uow = _make_uow()
    audit = _make_audit_service()

    handler = PlaceOrderOnHoldCommandHandler(repo, uow, audit_service=audit)
    command = PlaceOrderOnHoldCommand(
        tenant_id=tenant_id,
        sales_order_id=order_id,
        hold_reason="Customer requested delay",
        held_by=uuid.uuid4(),
    )

    await handler.handle(command)

    assert order.status == OrderStatus.ON_HOLD
    assert order.hold_reason == "Customer requested delay"
    repo.save.assert_awaited_once()
    uow.work.assert_awaited_once()


@pytest.mark.asyncio
async def test_hold_order_from_accepted():
    """Place ACCEPTED order on hold transitions to ON_HOLD."""
    tenant_id = uuid.uuid4()
    order_id = uuid.uuid4()

    order = _make_order(status=OrderStatus.ACCEPTED, tenant_id=tenant_id, order_id=order_id)
    repo = _make_repo(order)
    uow = _make_uow()

    handler = PlaceOrderOnHoldCommandHandler(repo, uow)
    command = PlaceOrderOnHoldCommand(
        tenant_id=tenant_id,
        sales_order_id=order_id,
        hold_reason="Payment issue",
        held_by=uuid.uuid4(),
    )

    await handler.handle(command)

    assert order.status == OrderStatus.ON_HOLD
    assert order.hold_reason == "Payment issue"


@pytest.mark.asyncio
async def test_hold_order_from_picking_raises():
    """Cannot place PICKING order on hold."""
    order = _make_order(status=OrderStatus.PICKING)
    repo = _make_repo(order)
    uow = _make_uow()

    handler = PlaceOrderOnHoldCommandHandler(repo, uow)
    command = PlaceOrderOnHoldCommand(
        tenant_id=order.tenant_id,
        sales_order_id=order.id,
        hold_reason="Too late",
        held_by=uuid.uuid4(),
    )

    with pytest.raises(InvalidTransitionError):
        await handler.handle(command)


# ── ReleaseOrderHoldCommandHandler Tests ─────────────────────────────────────


@pytest.mark.asyncio
async def test_release_hold_success():
    """Release ON_HOLD order transitions to ASSIGNED and clears hold_reason."""
    tenant_id = uuid.uuid4()
    order_id = uuid.uuid4()

    order = _make_order(status=OrderStatus.ON_HOLD, tenant_id=tenant_id, order_id=order_id)
    order.hold_reason = "Previous reason"
    repo = _make_repo(order)
    uow = _make_uow()
    audit = _make_audit_service()

    handler = ReleaseOrderHoldCommandHandler(repo, uow, audit_service=audit)
    command = ReleaseOrderHoldCommand(
        tenant_id=tenant_id,
        sales_order_id=order_id,
        released_by=uuid.uuid4(),
    )

    await handler.handle(command)

    assert order.status == OrderStatus.ASSIGNED
    assert order.hold_reason is None
    repo.save.assert_awaited_once()
    uow.work.assert_awaited_once()


@pytest.mark.asyncio
async def test_release_hold_from_assigned_raises():
    """Cannot release hold on an order that is not ON_HOLD."""
    order = _make_order(status=OrderStatus.ASSIGNED)
    repo = _make_repo(order)
    uow = _make_uow()

    handler = ReleaseOrderHoldCommandHandler(repo, uow)
    command = ReleaseOrderHoldCommand(
        tenant_id=order.tenant_id,
        sales_order_id=order.id,
        released_by=uuid.uuid4(),
    )

    with pytest.raises(InvalidTransitionError):
        await handler.handle(command)


# ── AdminCancelOrderCommandHandler Tests ─────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_cancel_from_pending_manual():
    """Admin cancel PENDING_MANUAL_ASSIGNMENT order transitions to CANCELLED."""
    tenant_id = uuid.uuid4()
    order_id = uuid.uuid4()
    user_id = uuid.uuid4()

    order = _make_order(status=OrderStatus.PENDING_MANUAL_ASSIGNMENT, tenant_id=tenant_id, order_id=order_id)
    repo = _make_repo(order)
    uow = _make_uow()
    audit = _make_audit_service()
    inv_service = _make_inventory_service()

    handler = AdminCancelOrderCommandHandler(repo, inv_service, uow, audit_service=audit)
    command = AdminCancelOrderCommand(
        tenant_id=tenant_id,
        sales_order_id=order_id,
        reason="No stock available",
        cancelled_by=user_id,
    )

    await handler.handle(command)

    assert order.status == OrderStatus.CANCELLED
    inv_service.release_all_reservations_for_order.assert_awaited_once_with(
        tenant_id=tenant_id,
        order_id=order_id,
        created_by=user_id,
    )
    repo.save.assert_awaited_once()
    uow.work.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_cancel_from_assigned():
    """Admin cancel ASSIGNED order transitions to CANCELLED and releases inventory."""
    tenant_id = uuid.uuid4()
    order_id = uuid.uuid4()
    user_id = uuid.uuid4()

    order = _make_order(status=OrderStatus.ASSIGNED, tenant_id=tenant_id, order_id=order_id)
    repo = _make_repo(order)
    uow = _make_uow()
    inv_service = _make_inventory_service()

    handler = AdminCancelOrderCommandHandler(repo, inv_service, uow)
    command = AdminCancelOrderCommand(
        tenant_id=tenant_id,
        sales_order_id=order_id,
        reason="Client requested",
        cancelled_by=user_id,
    )

    await handler.handle(command)

    assert order.status == OrderStatus.CANCELLED
    inv_service.release_all_reservations_for_order.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_cancel_from_picking_raises():
    """Cannot cancel an order that is already in PICKING state."""
    order = _make_order(status=OrderStatus.PICKING)
    repo = _make_repo(order)
    uow = _make_uow()
    inv_service = _make_inventory_service()

    handler = AdminCancelOrderCommandHandler(repo, inv_service, uow)
    command = AdminCancelOrderCommand(
        tenant_id=order.tenant_id,
        sales_order_id=order.id,
        reason="Too late",
        cancelled_by=uuid.uuid4(),
    )

    with pytest.raises(InvalidTransitionError):
        await handler.handle(command)

    # Ensure reservations were NOT released since the transition failed
    inv_service.release_all_reservations_for_order.assert_not_awaited()
