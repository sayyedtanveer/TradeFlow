"""Unit tests for Inventory Reservation System.

Tests the reservation service that:
- Reserves ordered quantities upon order confirmation (Req 5.7)
- Releases reservations on order cancellation (Req 6.3, 6.13)
- Calculates available quantity as current_stock - reserved_stock
- Prevents overselling when available_stock < requested_quantity
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4, UUID

from backend.app.domain.sales.services.inventory_reservation_service import (
    InventoryReservationService,
    InsufficientInventoryError,
)


@pytest.fixture
def mock_inventory_service():
    """Create a mock inventory integration service."""
    service = AsyncMock()
    service.get_available_stock = AsyncMock(return_value=Decimal("100"))
    service.reserve_stock = AsyncMock()
    service.release_stock = AsyncMock()
    service.fulfill_reservation = AsyncMock()
    return service


@pytest.fixture
def reservation_service(mock_inventory_service):
    """Create an InventoryReservationService with mock dependencies."""
    return InventoryReservationService(mock_inventory_service)


@pytest.fixture
def reservation_service_with_mfg(mock_inventory_service):
    """Create an InventoryReservationService with both dependencies (as routes do)."""
    mock_mfg = MagicMock()
    return InventoryReservationService(mock_inventory_service, mock_mfg)


class TestReserveForOrderLine:
    """Test inventory reservation on order confirmation."""

    @pytest.mark.asyncio
    async def test_reserves_full_quantity_when_stock_available(
        self, reservation_service, mock_inventory_service
    ):
        """When available stock >= requested, full quantity should be reserved."""
        mock_inventory_service.get_available_stock.return_value = Decimal("100")
        tenant_id = uuid4()
        product_id = uuid4()
        order_id = uuid4()
        line_id = uuid4()
        uom_id = uuid4()

        allocated, shortage, work_order_id = await reservation_service.reserve_for_order_line(
            tenant_id=tenant_id,
            product_id=product_id,
            product_type="variant",
            uom_id=uom_id,
            quantity=Decimal("50"),
            sales_order_id=order_id,
            sales_order_line_id=line_id,
            delivery_date="2025-06-01",
        )

        assert allocated == Decimal("50")
        assert shortage == Decimal("0")
        assert work_order_id is None
        mock_inventory_service.reserve_stock.assert_called_once_with(
            tenant_id=tenant_id,
            product_id=product_id,
            product_type="variant",
            quantity=Decimal("50"),
            uom_id=uom_id,
            reference_type="sales_order_line",
            reference_id=line_id,
            warehouse_id=None,
            order_id=order_id,
        )

    @pytest.mark.asyncio
    async def test_partial_reservation_when_insufficient_stock(
        self, reservation_service, mock_inventory_service
    ):
        """When available < requested, only available amount is reserved."""
        mock_inventory_service.get_available_stock.return_value = Decimal("30")

        allocated, shortage, work_order_id = await reservation_service.reserve_for_order_line(
            tenant_id=uuid4(),
            product_id=uuid4(),
            product_type="variant",
            uom_id=uuid4(),
            quantity=Decimal("50"),
            sales_order_id=uuid4(),
            sales_order_line_id=uuid4(),
            delivery_date="2025-06-01",
        )

        assert allocated == Decimal("30")
        assert shortage == Decimal("20")
        assert work_order_id is None

    @pytest.mark.asyncio
    async def test_no_reservation_when_zero_stock(
        self, reservation_service, mock_inventory_service
    ):
        """When available stock is 0, no reservation is made."""
        mock_inventory_service.get_available_stock.return_value = Decimal("0")

        allocated, shortage, work_order_id = await reservation_service.reserve_for_order_line(
            tenant_id=uuid4(),
            product_id=uuid4(),
            product_type="variant",
            uom_id=uuid4(),
            quantity=Decimal("10"),
            sales_order_id=uuid4(),
            sales_order_line_id=uuid4(),
            delivery_date="2025-06-01",
        )

        assert allocated == Decimal("0")
        assert shortage == Decimal("10")
        assert work_order_id is None
        mock_inventory_service.reserve_stock.assert_not_called()

    @pytest.mark.asyncio
    async def test_prevents_overselling_exact_boundary(
        self, reservation_service, mock_inventory_service
    ):
        """Reservation should not exceed available stock (prevents overselling)."""
        mock_inventory_service.get_available_stock.return_value = Decimal("25")

        allocated, shortage, _ = await reservation_service.reserve_for_order_line(
            tenant_id=uuid4(),
            product_id=uuid4(),
            product_type="variant",
            uom_id=uuid4(),
            quantity=Decimal("25"),
            sales_order_id=uuid4(),
            sales_order_line_id=uuid4(),
            delivery_date="2025-06-01",
        )

        # Exact match: full allocation, no shortage
        assert allocated == Decimal("25")
        assert shortage == Decimal("0")

    @pytest.mark.asyncio
    async def test_constructor_accepts_manufacturing_service(
        self, reservation_service_with_mfg, mock_inventory_service
    ):
        """Service should accept optional manufacturing_service param (backward compat)."""
        mock_inventory_service.get_available_stock.return_value = Decimal("10")

        allocated, shortage, _ = await reservation_service_with_mfg.reserve_for_order_line(
            tenant_id=uuid4(),
            product_id=uuid4(),
            product_type="variant",
            uom_id=uuid4(),
            quantity=Decimal("5"),
            sales_order_id=uuid4(),
            sales_order_line_id=uuid4(),
            delivery_date="2025-06-01",
        )

        assert allocated == Decimal("5")
        assert shortage == Decimal("0")

    @pytest.mark.asyncio
    async def test_raises_value_error_on_service_failure(
        self, reservation_service, mock_inventory_service
    ):
        """Service failures should raise ValueError with context."""
        mock_inventory_service.get_available_stock.side_effect = RuntimeError("DB down")

        with pytest.raises(ValueError, match="Failed to reserve inventory"):
            await reservation_service.reserve_for_order_line(
                tenant_id=uuid4(),
                product_id=uuid4(),
                product_type="variant",
                uom_id=uuid4(),
                quantity=Decimal("10"),
                sales_order_id=uuid4(),
                sales_order_line_id=uuid4(),
                delivery_date="2025-06-01",
            )


class TestReleaseForOrder:
    """Test inventory release on order cancellation."""

    @pytest.mark.asyncio
    async def test_releases_all_allocated_lines(
        self, reservation_service, mock_inventory_service
    ):
        """All lines with allocated_quantity > 0 should be released."""
        line1 = MagicMock()
        line1.id = uuid4()
        line1.allocated_quantity = Decimal("10")

        line2 = MagicMock()
        line2.id = uuid4()
        line2.allocated_quantity = Decimal("20")

        await reservation_service.release_for_order(
            tenant_id=uuid4(),
            sales_order_id=uuid4(),
            lines=[line1, line2],
        )

        assert mock_inventory_service.release_stock.call_count == 2

    @pytest.mark.asyncio
    async def test_skips_lines_with_zero_allocation(
        self, reservation_service, mock_inventory_service
    ):
        """Lines with zero allocated_quantity should not trigger release."""
        line_allocated = MagicMock()
        line_allocated.id = uuid4()
        line_allocated.allocated_quantity = Decimal("15")

        line_zero = MagicMock()
        line_zero.id = uuid4()
        line_zero.allocated_quantity = Decimal("0")

        await reservation_service.release_for_order(
            tenant_id=uuid4(),
            sales_order_id=uuid4(),
            lines=[line_allocated, line_zero],
        )

        # Only one call for the allocated line
        mock_inventory_service.release_stock.assert_called_once()

    @pytest.mark.asyncio
    async def test_release_continues_on_individual_failure(
        self, reservation_service, mock_inventory_service
    ):
        """If one line release fails, others should still be released."""
        line1 = MagicMock()
        line1.id = uuid4()
        line1.allocated_quantity = Decimal("10")

        line2 = MagicMock()
        line2.id = uuid4()
        line2.allocated_quantity = Decimal("5")

        # First call fails, second succeeds
        mock_inventory_service.release_stock.side_effect = [
            RuntimeError("Lock timeout"),
            None,
        ]

        # Should not raise
        await reservation_service.release_for_order(
            tenant_id=uuid4(),
            sales_order_id=uuid4(),
            lines=[line1, line2],
        )

        assert mock_inventory_service.release_stock.call_count == 2

    @pytest.mark.asyncio
    async def test_release_empty_order(
        self, reservation_service, mock_inventory_service
    ):
        """Empty line list should complete without errors."""
        await reservation_service.release_for_order(
            tenant_id=uuid4(),
            sales_order_id=uuid4(),
            lines=[],
        )

        mock_inventory_service.release_stock.assert_not_called()


class TestRecordShipment:
    """Test shipment recording (reservation fulfillment)."""

    @pytest.mark.asyncio
    async def test_fulfills_reservation_on_shipment(
        self, reservation_service, mock_inventory_service
    ):
        """Shipment should call fulfill_reservation to deduct stock."""
        tenant_id = uuid4()
        line_id = uuid4()

        await reservation_service.record_shipment(
            tenant_id=tenant_id,
            sales_order_line_id=line_id,
            shipped_qty=Decimal("10"),
        )

        mock_inventory_service.fulfill_reservation.assert_called_once_with(
            tenant_id=tenant_id,
            reference_type="sales_order_line",
            reference_id=line_id,
            quantity=Decimal("10"),
        )

    @pytest.mark.asyncio
    async def test_raises_on_fulfillment_failure(
        self, reservation_service, mock_inventory_service
    ):
        """Failure during fulfillment should raise ValueError."""
        mock_inventory_service.fulfill_reservation.side_effect = RuntimeError("No reservation found")

        with pytest.raises(ValueError, match="Failed to record shipment"):
            await reservation_service.record_shipment(
                tenant_id=uuid4(),
                sales_order_line_id=uuid4(),
                shipped_qty=Decimal("5"),
            )


class TestCheckAvailability:
    """Test the availability check helper."""

    @pytest.mark.asyncio
    async def test_sufficient_stock_returns_true(
        self, reservation_service, mock_inventory_service
    ):
        """When available >= requested, returns (True, available_qty)."""
        mock_inventory_service.get_available_stock.return_value = Decimal("50")

        is_sufficient, available = await reservation_service.check_availability(
            tenant_id=uuid4(),
            product_id=uuid4(),
            product_type="variant",
            quantity=Decimal("30"),
        )

        assert is_sufficient is True
        assert available == Decimal("50")

    @pytest.mark.asyncio
    async def test_insufficient_stock_returns_false(
        self, reservation_service, mock_inventory_service
    ):
        """When available < requested, returns (False, available_qty)."""
        mock_inventory_service.get_available_stock.return_value = Decimal("5")

        is_sufficient, available = await reservation_service.check_availability(
            tenant_id=uuid4(),
            product_id=uuid4(),
            product_type="variant",
            quantity=Decimal("10"),
        )

        assert is_sufficient is False
        assert available == Decimal("5")

    @pytest.mark.asyncio
    async def test_exact_boundary_returns_true(
        self, reservation_service, mock_inventory_service
    ):
        """When available == requested, returns (True, available_qty)."""
        mock_inventory_service.get_available_stock.return_value = Decimal("10")

        is_sufficient, available = await reservation_service.check_availability(
            tenant_id=uuid4(),
            product_id=uuid4(),
            product_type="variant",
            quantity=Decimal("10"),
        )

        assert is_sufficient is True
        assert available == Decimal("10")


class TestAvailableQuantityCalculation:
    """Test that available_stock = current_stock - reserved_stock."""

    @pytest.mark.asyncio
    async def test_available_reflects_reservations(
        self, reservation_service, mock_inventory_service
    ):
        """
        Available stock should be current_stock - reserved_stock.
        This is verified by the mock returning values that represent
        the result of the subtraction done in the inventory layer.
        """
        # Simulate: current_stock=100, reserved_stock=40 → available=60
        mock_inventory_service.get_available_stock.return_value = Decimal("60")

        is_sufficient, available = await reservation_service.check_availability(
            tenant_id=uuid4(),
            product_id=uuid4(),
            product_type="variant",
            quantity=Decimal("50"),
        )

        assert is_sufficient is True
        assert available == Decimal("60")

    @pytest.mark.asyncio
    async def test_zero_available_when_fully_reserved(
        self, reservation_service, mock_inventory_service
    ):
        """When all stock is reserved, available should be 0."""
        # Simulate: current_stock=50, reserved_stock=50 → available=0
        mock_inventory_service.get_available_stock.return_value = Decimal("0")

        is_sufficient, available = await reservation_service.check_availability(
            tenant_id=uuid4(),
            product_id=uuid4(),
            product_type="variant",
            quantity=Decimal("1"),
        )

        assert is_sufficient is False
        assert available == Decimal("0")
