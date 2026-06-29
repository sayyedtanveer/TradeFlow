"""Unit tests for InventoryValidationHandler.

Tests the three outcome paths when an order.placed event is received:
1. SUCCESS: Single warehouse can fulfill → ASSIGNED + notify warehouse users
2. PARTIAL: No single warehouse but total sufficient → PENDING_MANUAL_ASSIGNMENT + notify Admin
3. FAILURE: Total stock insufficient → CANCELLED + release reservations + notify Client

Validates: Requirements 6.1, 6.2, 6.3, 6.4
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from backend.app.application.sales.events.inventory_validation_handler import (
    InventoryValidationHandler,
)
from backend.app.application.sales.events.order_placed_event import (
    OrderPlacedEvent,
    OrderLineItem,
)
from backend.app.domain.sales.value_objects.order_status import OrderStatus


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def order_id():
    return uuid.uuid4()


@pytest.fixture
def client_id():
    return uuid.uuid4()


@pytest.fixture
def warehouse_a_id():
    return uuid.uuid4()


@pytest.fixture
def warehouse_b_id():
    return uuid.uuid4()


@pytest.fixture
def product_a_id():
    return uuid.uuid4()


@pytest.fixture
def product_b_id():
    return uuid.uuid4()


@pytest.fixture
def uom_id():
    return uuid.uuid4()


@pytest.fixture
def mock_connection_manager():
    cm = AsyncMock()
    cm.broadcast_to_tenant = AsyncMock()
    cm.send_to_user = AsyncMock()
    return cm


@pytest.fixture
def mock_audit_service():
    service = AsyncMock()
    service.log_action = AsyncMock()
    return service


@pytest.fixture
def make_event(tenant_id, order_id, client_id):
    """Factory to create OrderPlacedEvent with custom line items."""
    def _make(lines: list[OrderLineItem]) -> OrderPlacedEvent:
        return OrderPlacedEvent(
            aggregate_id=order_id,
            tenant_id=tenant_id,
            order_id=order_id,
            order_number="SO-20250101-001",
            client_id=client_id,
            lines=lines,
        )
    return _make


@pytest.fixture
def make_line(uom_id):
    """Factory to create OrderLineItem."""
    def _make(product_id: uuid.UUID, quantity: float, product_type: str = "finished_product"):
        return OrderLineItem(
            line_id=uuid.uuid4(),
            product_id=product_id,
            product_type=product_type,
            uom_id=uom_id,
            quantity=quantity,
        )
    return _make


# ─── Test: Successful warehouse assignment ────────────────────────────────────


class TestInventoryValidationSuccess:
    """Test case where a single warehouse can fulfill all line items."""

    @pytest.mark.asyncio
    async def test_assigns_to_warehouse_when_stock_available(
        self,
        tenant_id,
        order_id,
        client_id,
        warehouse_a_id,
        product_a_id,
        product_b_id,
        uom_id,
        mock_connection_manager,
        mock_audit_service,
        make_event,
        make_line,
    ):
        """When a warehouse has sufficient stock for all items, order transitions to ASSIGNED."""
        lines = [
            make_line(product_a_id, 10.0),
            make_line(product_b_id, 5.0),
        ]
        event = make_event(lines)

        # Create a mock session factory and session
        mock_session = AsyncMock()
        mock_session_factory = MagicMock()

        # Mock the warehouse query result
        @dataclass
        class FakeWarehouse:
            id: uuid.UUID
            name: str
            is_active: bool = True
            is_deleted: bool = False
            tenant_id: uuid.UUID = None

        warehouse = FakeWarehouse(id=warehouse_a_id, name="Warehouse A", tenant_id=tenant_id)

        # Mock the order model
        @dataclass
        class FakeOrderModel:
            id: uuid.UUID
            tenant_id: uuid.UUID
            status: str = "PENDING_INVENTORY_VALIDATION"
            assigned_warehouse_id: uuid.UUID = None
            assigned_at: datetime = None

        order_model = FakeOrderModel(id=order_id, tenant_id=tenant_id)

        # Set up session mock to return warehouses and order
        warehouse_scalars = MagicMock()
        warehouse_scalars.all.return_value = [warehouse]

        order_scalars = MagicMock()
        order_scalars.scalar_one_or_none.return_value = order_model

        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            result = MagicMock()
            # First call = warehouse query, middle calls = material resolution + stock checks,
            # then reserve calls, then order query
            if call_count[0] == 1:
                # Warehouse query
                result.scalars.return_value = warehouse_scalars
            elif hasattr(stmt, '_where_criteria'):
                # For SELECT FOR UPDATE (order model) or material lookups
                result.scalar_one_or_none.return_value = order_model
                result.scalar_one.return_value = Decimal("100")
                result.scalars.return_value = warehouse_scalars
            else:
                result.scalar_one_or_none.return_value = product_a_id
                result.scalar_one.return_value = Decimal("100")
            return result

        mock_session.execute = mock_execute
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.begin = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=None),
            __aexit__=AsyncMock(return_value=None),
        ))

        # Set up context manager protocol for session_factory
        mock_session_factory.return_value = AsyncMock(
            __aenter__=AsyncMock(return_value=mock_session),
            __aexit__=AsyncMock(return_value=None),
        )

        handler = InventoryValidationHandler(
            session_factory=mock_session_factory,
            connection_manager=mock_connection_manager,
            audit_service=mock_audit_service,
        )

        # Patch the internal methods to focus on the assignment logic
        with patch.object(handler, '_get_active_warehouses', return_value=[
            {"id": warehouse_a_id, "name": "Warehouse A"}
        ]):
            with patch.object(handler, '_find_optimal_warehouse', return_value={
                "id": warehouse_a_id, "name": "Warehouse A"
            }):
                with patch.object(handler, '_assign_to_warehouse', new_callable=AsyncMock) as mock_assign:
                    await handler._validate_inventory(event)

                    mock_assign.assert_called_once()
                    call_kwargs = mock_assign.call_args[1]
                    assert call_kwargs["warehouse_id"] == warehouse_a_id
                    assert call_kwargs["warehouse_name"] == "Warehouse A"
                    assert call_kwargs["order_id"] == order_id


class TestInventoryValidationPendingManual:
    """Test case where no single warehouse can fulfill but total stock is sufficient."""

    @pytest.mark.asyncio
    async def test_pending_manual_when_no_single_warehouse(
        self,
        tenant_id,
        order_id,
        client_id,
        warehouse_a_id,
        warehouse_b_id,
        product_a_id,
        uom_id,
        mock_connection_manager,
        mock_audit_service,
        make_event,
        make_line,
    ):
        """When no single warehouse can fulfill but total is sufficient → PENDING_MANUAL_ASSIGNMENT."""
        lines = [make_line(product_a_id, 100.0)]
        event = make_event(lines)

        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session.begin = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=None),
            __aexit__=AsyncMock(return_value=None),
        ))

        mock_session_factory.return_value = AsyncMock(
            __aenter__=AsyncMock(return_value=mock_session),
            __aexit__=AsyncMock(return_value=None),
        )

        handler = InventoryValidationHandler(
            session_factory=mock_session_factory,
            connection_manager=mock_connection_manager,
            audit_service=mock_audit_service,
        )

        with patch.object(handler, '_get_active_warehouses', return_value=[
            {"id": warehouse_a_id, "name": "Warehouse A"},
            {"id": warehouse_b_id, "name": "Warehouse B"},
        ]):
            with patch.object(handler, '_find_optimal_warehouse', return_value=None):
                with patch.object(handler, '_check_total_availability', return_value=[]):
                    with patch.object(handler, '_mark_pending_manual_assignment', new_callable=AsyncMock) as mock_pending:
                        await handler._validate_inventory(event)

                        mock_pending.assert_called_once()
                        call_kwargs = mock_pending.call_args[1]
                        assert call_kwargs["order_id"] == order_id
                        assert call_kwargs["order_number"] == "SO-20250101-001"


class TestInventoryValidationCancellation:
    """Test case where total stock is insufficient — order is cancelled."""

    @pytest.mark.asyncio
    async def test_cancels_when_insufficient_total_stock(
        self,
        tenant_id,
        order_id,
        client_id,
        warehouse_a_id,
        product_a_id,
        uom_id,
        mock_connection_manager,
        mock_audit_service,
        make_event,
        make_line,
    ):
        """When total stock across all warehouses is insufficient → CANCELLED."""
        lines = [make_line(product_a_id, 1000.0)]
        event = make_event(lines)

        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session.begin = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=None),
            __aexit__=AsyncMock(return_value=None),
        ))

        mock_session_factory.return_value = AsyncMock(
            __aenter__=AsyncMock(return_value=mock_session),
            __aexit__=AsyncMock(return_value=None),
        )

        shortage_details = [{
            "product_id": str(product_a_id),
            "requested": 1000.0,
            "available": 50.0,
            "reason": "Insufficient stock across all warehouses",
        }]

        handler = InventoryValidationHandler(
            session_factory=mock_session_factory,
            connection_manager=mock_connection_manager,
            audit_service=mock_audit_service,
        )

        with patch.object(handler, '_get_active_warehouses', return_value=[
            {"id": warehouse_a_id, "name": "Warehouse A"},
        ]):
            with patch.object(handler, '_find_optimal_warehouse', return_value=None):
                with patch.object(handler, '_check_total_availability', return_value=shortage_details):
                    with patch.object(handler, '_cancel_order', new_callable=AsyncMock) as mock_cancel:
                        await handler._validate_inventory(event)

                        mock_cancel.assert_called_once()
                        call_kwargs = mock_cancel.call_args[1]
                        assert call_kwargs["order_id"] == order_id
                        assert call_kwargs["client_id"] == client_id
                        assert call_kwargs["shortage_details"] == shortage_details


class TestInventoryValidationNoWarehouses:
    """Test case where no active warehouses exist."""

    @pytest.mark.asyncio
    async def test_cancels_when_no_warehouses(
        self,
        tenant_id,
        order_id,
        client_id,
        product_a_id,
        uom_id,
        mock_connection_manager,
        mock_audit_service,
        make_event,
        make_line,
    ):
        """When no active warehouses exist → CANCELLED."""
        lines = [make_line(product_a_id, 10.0)]
        event = make_event(lines)

        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session.begin = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=None),
            __aexit__=AsyncMock(return_value=None),
        ))

        mock_session_factory.return_value = AsyncMock(
            __aenter__=AsyncMock(return_value=mock_session),
            __aexit__=AsyncMock(return_value=None),
        )

        handler = InventoryValidationHandler(
            session_factory=mock_session_factory,
            connection_manager=mock_connection_manager,
            audit_service=mock_audit_service,
        )

        with patch.object(handler, '_get_active_warehouses', return_value=[]):
            with patch.object(handler, '_cancel_order', new_callable=AsyncMock) as mock_cancel:
                await handler._validate_inventory(event)

                mock_cancel.assert_called_once()
                call_kwargs = mock_cancel.call_args[1]
                assert call_kwargs["order_id"] == order_id
                assert len(call_kwargs["shortage_details"]) == 1


class TestInventoryValidationNotifications:
    """Test notifications are sent correctly for each outcome."""

    @pytest.mark.asyncio
    async def test_warehouse_users_notified_on_assignment(
        self, tenant_id, mock_connection_manager
    ):
        """Warehouse users receive notification when order is assigned."""
        handler = InventoryValidationHandler(
            session_factory=MagicMock(),
            connection_manager=mock_connection_manager,
        )

        order_id = uuid.uuid4()
        warehouse_id = uuid.uuid4()

        await handler._notify_warehouse_users(
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
            order_id=order_id,
            order_number="SO-001",
        )

        mock_connection_manager.broadcast_to_tenant.assert_called_once()
        call_kwargs = mock_connection_manager.broadcast_to_tenant.call_args[1]
        assert call_kwargs["tenant_id"] == tenant_id
        payload = call_kwargs["payload"]
        assert payload["type"] == "ORDER_ASSIGNED"
        assert str(order_id) in payload["data"]["order_id"]

    @pytest.mark.asyncio
    async def test_client_notified_on_cancellation(
        self, tenant_id, client_id, mock_connection_manager
    ):
        """Client receives cancellation notification with shortage details."""
        handler = InventoryValidationHandler(
            session_factory=MagicMock(),
            connection_manager=mock_connection_manager,
        )

        order_id = uuid.uuid4()
        shortage_details = [{"product_id": "abc", "requested": 10, "available": 0}]

        await handler._notify_client_cancellation(
            tenant_id=tenant_id,
            client_id=client_id,
            order_id=order_id,
            order_number="SO-001",
            shortage_details=shortage_details,
        )

        mock_connection_manager.send_to_user.assert_called_once()
        call_kwargs = mock_connection_manager.send_to_user.call_args[1]
        assert call_kwargs["tenant_id"] == tenant_id
        assert call_kwargs["user_id"] == client_id
        payload = call_kwargs["payload"]
        assert payload["type"] == "ORDER_CANCELLED"
        assert payload["data"]["shortage_details"] == shortage_details

    @pytest.mark.asyncio
    async def test_admin_notified_on_pending_manual(
        self, tenant_id, mock_connection_manager
    ):
        """Admin receives notification when manual assignment is required."""
        handler = InventoryValidationHandler(
            session_factory=MagicMock(),
            connection_manager=mock_connection_manager,
        )

        order_id = uuid.uuid4()

        await handler._notify_admin_manual_assignment(
            tenant_id=tenant_id,
            order_id=order_id,
            order_number="SO-001",
        )

        mock_connection_manager.broadcast_to_tenant.assert_called_once()
        call_kwargs = mock_connection_manager.broadcast_to_tenant.call_args[1]
        assert call_kwargs["tenant_id"] == tenant_id
        payload = call_kwargs["payload"]
        assert payload["type"] == "ORDER_NEEDS_MANUAL_ASSIGNMENT"


class TestEventType:
    """Test the handler correctly subscribes to order.placed."""

    def test_event_type_is_order_placed(self, mock_connection_manager):
        handler = InventoryValidationHandler(
            session_factory=MagicMock(),
            connection_manager=mock_connection_manager,
        )
        assert handler.event_type == "order.placed"


class TestOrderPlacedEvent:
    """Test OrderPlacedEvent dataclass."""

    def test_event_creation(self, tenant_id, order_id, client_id, product_a_id, uom_id):
        """OrderPlacedEvent is created with correct event_type."""
        line = OrderLineItem(
            line_id=uuid.uuid4(),
            product_id=product_a_id,
            product_type="finished_product",
            uom_id=uom_id,
            quantity=10.0,
        )
        event = OrderPlacedEvent(
            aggregate_id=order_id,
            tenant_id=tenant_id,
            order_id=order_id,
            order_number="SO-001",
            client_id=client_id,
            lines=[line],
        )
        assert event.event_type == "order.placed"
        assert event.order_id == order_id
        assert event.client_id == client_id
        assert len(event.lines) == 1
        assert event.lines[0].quantity == 10.0
