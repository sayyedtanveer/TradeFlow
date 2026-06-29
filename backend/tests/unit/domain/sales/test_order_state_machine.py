"""Unit tests for OrderStateMachine domain service.

Tests transition validation, invalid transition rejection (409 semantics),
terminal state detection, and audit logging integration.

Validates: Requirements 6.11, 6.12, 14.3
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.domain.sales.value_objects import OrderStatus, OrderNumber
from backend.app.domain.sales.value_objects.order_status import ORDER_STATUS_TRANSITIONS, get_allowed_transitions
from backend.app.domain.sales.services.order_state_machine import (
    OrderStateMachine,
    InvalidTransitionError,
)
from backend.app.domain.sales.entities import SalesOrder


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def state_machine():
    """Create an OrderStateMachine without audit service."""
    return OrderStateMachine()


@pytest.fixture
def mock_audit_service():
    """Create a mock audit service with async log_action."""
    service = AsyncMock()
    service.log_action = AsyncMock()
    return service


@pytest.fixture
def state_machine_with_audit(mock_audit_service):
    """Create an OrderStateMachine with a mock audit service."""
    return OrderStateMachine(audit_service=mock_audit_service)


@pytest.fixture
def make_order():
    """Factory to create a SalesOrder in a given status."""
    def _make(status: OrderStatus = OrderStatus.PENDING_INVENTORY_VALIDATION):
        order = SalesOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            order_number=OrderNumber.generate(1),
            client_id=uuid.uuid4(),
            order_date=date.today(),
            delivery_date=date.today() + timedelta(days=30),
            status=status,
        )
        return order
    return _make


# ─── Transition Map Completeness Tests ────────────────────────────────────────

class TestTransitionMap:
    """Verify the allowed transitions map is correctly defined."""

    def test_all_statuses_have_entries(self):
        """Every OrderStatus member must have an entry in the transitions map."""
        for status in OrderStatus:
            assert status in ORDER_STATUS_TRANSITIONS, (
                f"{status.value} missing from ORDER_STATUS_TRANSITIONS"
            )

    def test_pending_inventory_validation_transitions(self):
        """PENDING_INVENTORY_VALIDATION can go to ASSIGNED, PENDING_MANUAL_ASSIGNMENT, or CANCELLED."""
        allowed = ORDER_STATUS_TRANSITIONS[OrderStatus.PENDING_INVENTORY_VALIDATION]
        assert set(allowed) == {
            OrderStatus.ASSIGNED,
            OrderStatus.PENDING_MANUAL_ASSIGNMENT,
            OrderStatus.CANCELLED,
        }

    def test_pending_manual_assignment_transitions(self):
        """PENDING_MANUAL_ASSIGNMENT can go to ASSIGNED or CANCELLED."""
        allowed = ORDER_STATUS_TRANSITIONS[OrderStatus.PENDING_MANUAL_ASSIGNMENT]
        assert set(allowed) == {OrderStatus.ASSIGNED, OrderStatus.CANCELLED}

    def test_assigned_transitions(self):
        """ASSIGNED can go to ACCEPTED, PENDING_MANUAL_ASSIGNMENT, ON_HOLD, or CANCELLED."""
        allowed = ORDER_STATUS_TRANSITIONS[OrderStatus.ASSIGNED]
        assert set(allowed) == {
            OrderStatus.ACCEPTED,
            OrderStatus.PENDING_MANUAL_ASSIGNMENT,
            OrderStatus.ON_HOLD,
            OrderStatus.CANCELLED,
        }

    def test_accepted_transitions(self):
        """ACCEPTED can go to PICKING or ON_HOLD."""
        allowed = ORDER_STATUS_TRANSITIONS[OrderStatus.ACCEPTED]
        assert set(allowed) == {OrderStatus.PICKING, OrderStatus.ON_HOLD}

    def test_picking_transitions(self):
        """PICKING can only go to PACKING."""
        allowed = ORDER_STATUS_TRANSITIONS[OrderStatus.PICKING]
        assert allowed == [OrderStatus.PACKING]

    def test_packing_transitions(self):
        """PACKING can only go to READY_FOR_DISPATCH."""
        allowed = ORDER_STATUS_TRANSITIONS[OrderStatus.PACKING]
        assert allowed == [OrderStatus.READY_FOR_DISPATCH]

    def test_ready_for_dispatch_transitions(self):
        """READY_FOR_DISPATCH can only go to DISPATCHED."""
        allowed = ORDER_STATUS_TRANSITIONS[OrderStatus.READY_FOR_DISPATCH]
        assert allowed == [OrderStatus.DISPATCHED]

    def test_dispatched_transitions(self):
        """DISPATCHED can only go to INVOICED."""
        allowed = ORDER_STATUS_TRANSITIONS[OrderStatus.DISPATCHED]
        assert allowed == [OrderStatus.INVOICED]

    def test_on_hold_transitions(self):
        """ON_HOLD can only go to ASSIGNED."""
        allowed = ORDER_STATUS_TRANSITIONS[OrderStatus.ON_HOLD]
        assert allowed == [OrderStatus.ASSIGNED]

    def test_invoiced_is_terminal(self):
        """INVOICED has no allowed transitions (terminal state)."""
        assert ORDER_STATUS_TRANSITIONS[OrderStatus.INVOICED] == []

    def test_cancelled_is_terminal(self):
        """CANCELLED has no allowed transitions (terminal state)."""
        assert ORDER_STATUS_TRANSITIONS[OrderStatus.CANCELLED] == []


# ─── can_transition Tests ─────────────────────────────────────────────────────

class TestCanTransition:
    """Tests for OrderStateMachine.can_transition() method."""

    def test_valid_transition_returns_true(self, state_machine):
        """Valid transitions return True."""
        assert state_machine.can_transition(
            OrderStatus.PENDING_INVENTORY_VALIDATION, OrderStatus.ASSIGNED
        ) is True

    def test_invalid_transition_returns_false(self, state_machine):
        """Invalid transitions return False."""
        assert state_machine.can_transition(
            OrderStatus.PENDING_INVENTORY_VALIDATION, OrderStatus.DISPATCHED
        ) is False

    def test_terminal_state_returns_false_for_any_target(self, state_machine):
        """Terminal states always return False for any target."""
        for target in OrderStatus:
            assert state_machine.can_transition(OrderStatus.CANCELLED, target) is False
            assert state_machine.can_transition(OrderStatus.INVOICED, target) is False

    def test_self_transition_not_allowed(self, state_machine):
        """Transitioning to the same state is not allowed."""
        for status in OrderStatus:
            assert state_machine.can_transition(status, status) is False


# ─── validate_transition Tests ────────────────────────────────────────────────

class TestValidateTransition:
    """Tests for OrderStateMachine.validate_transition() method."""

    def test_valid_transition_does_not_raise(self, state_machine):
        """Valid transitions pass without raising."""
        # Should not raise
        state_machine.validate_transition(
            OrderStatus.ASSIGNED, OrderStatus.ACCEPTED
        )

    def test_invalid_transition_raises_invalid_transition_error(self, state_machine):
        """Invalid transitions raise InvalidTransitionError."""
        with pytest.raises(InvalidTransitionError) as exc_info:
            state_machine.validate_transition(
                OrderStatus.PICKING, OrderStatus.DISPATCHED
            )
        
        err = exc_info.value
        assert err.current_status == OrderStatus.PICKING
        assert err.target_status == OrderStatus.DISPATCHED
        assert OrderStatus.PACKING in err.allowed_statuses

    def test_error_message_includes_current_and_allowed(self, state_machine):
        """InvalidTransitionError message includes current status and allowed transitions."""
        with pytest.raises(InvalidTransitionError) as exc_info:
            state_machine.validate_transition(
                OrderStatus.ACCEPTED, OrderStatus.DISPATCHED
            )
        
        message = str(exc_info.value)
        assert "ACCEPTED" in message
        assert "DISPATCHED" in message
        assert "PICKING" in message  # Allowed from ACCEPTED
        assert "ON_HOLD" in message  # Allowed from ACCEPTED

    def test_terminal_state_raises_with_empty_allowed(self, state_machine):
        """Transitioning from a terminal state raises with empty allowed list."""
        with pytest.raises(InvalidTransitionError) as exc_info:
            state_machine.validate_transition(
                OrderStatus.CANCELLED, OrderStatus.ASSIGNED
            )
        
        err = exc_info.value
        assert err.allowed_statuses == []


# ─── InvalidTransitionError Tests ─────────────────────────────────────────────

class TestInvalidTransitionError:
    """Tests for the InvalidTransitionError exception class."""

    def test_error_attributes(self):
        """InvalidTransitionError exposes current_status, target_status, and allowed_statuses."""
        err = InvalidTransitionError(
            OrderStatus.ASSIGNED, OrderStatus.INVOICED
        )
        assert err.current_status == OrderStatus.ASSIGNED
        assert err.target_status == OrderStatus.INVOICED
        assert set(err.allowed_statuses) == {
            OrderStatus.ACCEPTED,
            OrderStatus.PENDING_MANUAL_ASSIGNMENT,
            OrderStatus.ON_HOLD,
            OrderStatus.CANCELLED,
        }

    def test_error_string_format(self):
        """Error string includes the current, target, and allowed statuses."""
        err = InvalidTransitionError(
            OrderStatus.PICKING, OrderStatus.CANCELLED
        )
        msg = str(err)
        assert "PICKING" in msg
        assert "CANCELLED" in msg
        assert "PACKING" in msg


# ─── get_allowed_next_statuses Tests ──────────────────────────────────────────

class TestGetAllowedNextStatuses:
    """Tests for get_allowed_next_statuses method."""

    def test_returns_correct_list(self, state_machine):
        """Returns the correct list of allowed next statuses."""
        allowed = state_machine.get_allowed_next_statuses(OrderStatus.ASSIGNED)
        assert set(allowed) == {
            OrderStatus.ACCEPTED,
            OrderStatus.PENDING_MANUAL_ASSIGNMENT,
            OrderStatus.ON_HOLD,
            OrderStatus.CANCELLED,
        }

    def test_terminal_returns_empty(self, state_machine):
        """Terminal states return empty list."""
        assert state_machine.get_allowed_next_statuses(OrderStatus.INVOICED) == []
        assert state_machine.get_allowed_next_statuses(OrderStatus.CANCELLED) == []


# ─── is_terminal Tests ────────────────────────────────────────────────────────

class TestIsTerminal:
    """Tests for is_terminal method."""

    def test_invoiced_is_terminal(self, state_machine):
        assert state_machine.is_terminal(OrderStatus.INVOICED) is True

    def test_cancelled_is_terminal(self, state_machine):
        assert state_machine.is_terminal(OrderStatus.CANCELLED) is True

    def test_non_terminal_states(self, state_machine):
        """Non-terminal states return False."""
        non_terminal = [
            OrderStatus.PENDING_INVENTORY_VALIDATION,
            OrderStatus.PENDING_MANUAL_ASSIGNMENT,
            OrderStatus.ASSIGNED,
            OrderStatus.ACCEPTED,
            OrderStatus.PICKING,
            OrderStatus.PACKING,
            OrderStatus.READY_FOR_DISPATCH,
            OrderStatus.DISPATCHED,
            OrderStatus.ON_HOLD,
        ]
        for status in non_terminal:
            assert state_machine.is_terminal(status) is False, (
                f"{status.value} should not be terminal"
            )


# ─── execute_transition Tests (with audit) ────────────────────────────────────

class TestExecuteTransition:
    """Tests for execute_transition method with audit logging."""

    @pytest.mark.asyncio
    async def test_valid_transition_changes_order_status(
        self, state_machine_with_audit, make_order
    ):
        """execute_transition changes the order's status on valid transition."""
        order = make_order(OrderStatus.ASSIGNED)
        user_id = uuid.uuid4()

        await state_machine_with_audit.execute_transition(
            order=order,
            target_status=OrderStatus.ACCEPTED,
            acting_user_id=user_id,
        )

        assert order.status == OrderStatus.ACCEPTED

    @pytest.mark.asyncio
    async def test_invalid_transition_raises_and_does_not_change_status(
        self, state_machine_with_audit, make_order
    ):
        """execute_transition raises on invalid transition without changing status."""
        order = make_order(OrderStatus.PICKING)
        original_status = order.status

        with pytest.raises(InvalidTransitionError):
            await state_machine_with_audit.execute_transition(
                order=order,
                target_status=OrderStatus.DISPATCHED,
                acting_user_id=uuid.uuid4(),
            )

        # Status unchanged
        assert order.status == original_status

    @pytest.mark.asyncio
    async def test_audit_log_called_on_valid_transition(
        self, state_machine_with_audit, mock_audit_service, make_order
    ):
        """Audit service is called with correct data after a valid transition."""
        order = make_order(OrderStatus.READY_FOR_DISPATCH)
        user_id = uuid.uuid4()

        await state_machine_with_audit.execute_transition(
            order=order,
            target_status=OrderStatus.DISPATCHED,
            acting_user_id=user_id,
        )

        # Verify audit_service.log_action was called
        mock_audit_service.log_action.assert_called_once()
        call_kwargs = mock_audit_service.log_action.call_args[1]

        assert call_kwargs["action"] == "ORDER_STATUS_TRANSITION"
        assert call_kwargs["entity_type"] == "sales_order"
        assert call_kwargs["entity_id"] == order.id
        assert call_kwargs["before_value"] == {"status": "READY_FOR_DISPATCH"}
        assert call_kwargs["after_value"] == {"status": "DISPATCHED"}
        # Extra contains acting user, previous/new status, and timestamp
        extra = call_kwargs["extra"]
        assert extra["previous_status"] == "READY_FOR_DISPATCH"
        assert extra["new_status"] == "DISPATCHED"
        assert extra["acting_user_id"] == str(user_id)
        assert "transition_timestamp" in extra

    @pytest.mark.asyncio
    async def test_audit_not_called_on_invalid_transition(
        self, state_machine_with_audit, mock_audit_service, make_order
    ):
        """Audit service is NOT called when transition is invalid."""
        order = make_order(OrderStatus.PICKING)

        with pytest.raises(InvalidTransitionError):
            await state_machine_with_audit.execute_transition(
                order=order,
                target_status=OrderStatus.CANCELLED,
                acting_user_id=uuid.uuid4(),
            )

        mock_audit_service.log_action.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_audit_service_does_not_fail(self, state_machine, make_order):
        """execute_transition works without audit service (no crash)."""
        order = make_order(OrderStatus.DISPATCHED)

        await state_machine.execute_transition(
            order=order,
            target_status=OrderStatus.INVOICED,
            acting_user_id=uuid.uuid4(),
        )

        assert order.status == OrderStatus.INVOICED


# ─── Full Workflow Path Test ──────────────────────────────────────────────────

class TestFullWorkflowPath:
    """Test the complete happy-path workflow through all statuses."""

    @pytest.mark.asyncio
    async def test_full_happy_path(self, state_machine_with_audit, make_order):
        """Test the entire order lifecycle from placement to invoicing."""
        order = make_order(OrderStatus.PENDING_INVENTORY_VALIDATION)
        user_id = uuid.uuid4()

        transitions = [
            OrderStatus.ASSIGNED,
            OrderStatus.ACCEPTED,
            OrderStatus.PICKING,
            OrderStatus.PACKING,
            OrderStatus.READY_FOR_DISPATCH,
            OrderStatus.DISPATCHED,
            OrderStatus.INVOICED,
        ]

        for target in transitions:
            await state_machine_with_audit.execute_transition(
                order=order,
                target_status=target,
                acting_user_id=user_id,
            )
            assert order.status == target

    @pytest.mark.asyncio
    async def test_hold_and_release_path(self, state_machine_with_audit, make_order):
        """Test placing on hold from ASSIGNED and releasing back."""
        order = make_order(OrderStatus.ASSIGNED)
        user_id = uuid.uuid4()

        # Place on hold
        await state_machine_with_audit.execute_transition(
            order=order, target_status=OrderStatus.ON_HOLD, acting_user_id=user_id
        )
        assert order.status == OrderStatus.ON_HOLD

        # Release hold (back to ASSIGNED)
        await state_machine_with_audit.execute_transition(
            order=order, target_status=OrderStatus.ASSIGNED, acting_user_id=user_id
        )
        assert order.status == OrderStatus.ASSIGNED

    @pytest.mark.asyncio
    async def test_decline_path(self, state_machine_with_audit, make_order):
        """Test warehouse declining an assigned order."""
        order = make_order(OrderStatus.ASSIGNED)
        user_id = uuid.uuid4()

        # Decline → PENDING_MANUAL_ASSIGNMENT
        await state_machine_with_audit.execute_transition(
            order=order,
            target_status=OrderStatus.PENDING_MANUAL_ASSIGNMENT,
            acting_user_id=user_id,
        )
        assert order.status == OrderStatus.PENDING_MANUAL_ASSIGNMENT

        # Admin reassigns
        await state_machine_with_audit.execute_transition(
            order=order, target_status=OrderStatus.ASSIGNED, acting_user_id=user_id
        )
        assert order.status == OrderStatus.ASSIGNED

    @pytest.mark.asyncio
    async def test_cancellation_from_pending_manual_assignment(
        self, state_machine_with_audit, make_order
    ):
        """Test cancellation from PENDING_MANUAL_ASSIGNMENT."""
        order = make_order(OrderStatus.PENDING_MANUAL_ASSIGNMENT)

        await state_machine_with_audit.execute_transition(
            order=order,
            target_status=OrderStatus.CANCELLED,
            acting_user_id=uuid.uuid4(),
        )
        assert order.status == OrderStatus.CANCELLED


# ─── get_allowed_transitions helper Tests ─────────────────────────────────────

class TestGetAllowedTransitionsHelper:
    """Tests for the module-level get_allowed_transitions helper."""

    def test_returns_list_for_valid_status(self):
        result = get_allowed_transitions(OrderStatus.ACCEPTED)
        assert OrderStatus.PICKING in result
        assert OrderStatus.ON_HOLD in result

    def test_returns_empty_for_terminal(self):
        assert get_allowed_transitions(OrderStatus.CANCELLED) == []
        assert get_allowed_transitions(OrderStatus.INVOICED) == []
