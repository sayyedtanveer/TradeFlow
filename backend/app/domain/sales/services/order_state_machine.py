"""Order State Machine Domain Service.

Provides transition validation logic for the distribution order workflow.
This service encapsulates the state machine rules and can be used by
application-layer command handlers to validate and perform transitions.

Every status transition is recorded in the audit trail with:
- timestamp
- acting user_id
- previous status
- new status
- entity_id (the order)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.app.domain.sales.value_objects.order_status import (
    OrderStatus,
    ORDER_STATUS_TRANSITIONS,
    get_allowed_transitions,
)


class InvalidTransitionError(Exception):
    """Raised when an order status transition is not allowed by the state machine.

    Attributes:
        current_status: The order's current status.
        target_status: The attempted target status.
        allowed_statuses: List of statuses the order can legally transition to.
    """

    def __init__(self, current_status: OrderStatus, target_status: OrderStatus):
        self.current_status = current_status
        self.target_status = target_status
        self.allowed_statuses = get_allowed_transitions(current_status)
        allowed_names = [s.value for s in self.allowed_statuses]
        super().__init__(
            f"Cannot transition from {current_status.value} to {target_status.value}. "
            f"Allowed transitions: {allowed_names}"
        )


class OrderStateMachine:
    """
    Domain service that validates and enforces order status transitions.

    Usage without audit logging:
        machine = OrderStateMachine()
        machine.validate_transition(current_status, target_status)  # raises on invalid

    Usage with audit logging (preferred in application layer):
        machine = OrderStateMachine(audit_service=container.audit_service)
        await machine.execute_transition(
            order=order,
            target_status=OrderStatus.ASSIGNED,
            acting_user_id=user_id,
        )
    """

    def __init__(self, audit_service=None) -> None:
        self._transitions = ORDER_STATUS_TRANSITIONS
        self._audit_service = audit_service

    @property
    def transitions(self) -> dict[OrderStatus, list[OrderStatus]]:
        """Return the full transitions map (read-only reference)."""
        return self._transitions

    def can_transition(self, current: OrderStatus, target: OrderStatus) -> bool:
        """
        Check whether transitioning from `current` to `target` is allowed.

        Args:
            current: The current order status.
            target: The desired next status.

        Returns:
            True if the transition is permitted by the state machine.
        """
        return target in self._transitions.get(current, [])

    def validate_transition(self, current: OrderStatus, target: OrderStatus) -> None:
        """
        Validate that a transition is allowed, raising on failure.

        Args:
            current: The current order status.
            target: The desired next status.

        Raises:
            InvalidTransitionError: If the transition is not allowed.
        """
        if not self.can_transition(current, target):
            raise InvalidTransitionError(current, target)

    def get_allowed_next_statuses(self, current: OrderStatus) -> list[OrderStatus]:
        """
        Return the list of statuses reachable from the given status.

        Args:
            current: The current order status.

        Returns:
            List of allowed target statuses.
        """
        return list(self._transitions.get(current, []))

    def is_terminal(self, status: OrderStatus) -> bool:
        """Check whether the given status is terminal (no outgoing transitions)."""
        return len(self._transitions.get(status, [])) == 0

    async def execute_transition(
        self,
        order,
        target_status: OrderStatus,
        acting_user_id: Optional[uuid.UUID] = None,
    ) -> None:
        """
        Validate a transition, perform it on the order entity, and record it
        in the audit trail.

        This is the preferred way to transition order status in application-layer
        command handlers because it guarantees the audit record is always written.

        Args:
            order: The SalesOrder entity (must expose .id, .status, .transition_to()).
            target_status: The desired next status.
            acting_user_id: The user performing the transition.

        Raises:
            InvalidTransitionError: If the transition is not allowed.
        """
        previous_status = order.status

        # Validate first — raises InvalidTransitionError if not allowed
        self.validate_transition(previous_status, target_status)

        # Perform the transition on the entity
        order.transition_to(target_status)

        # Record audit log entry
        await self._record_transition_audit(
            entity_id=order.id,
            previous_status=previous_status,
            new_status=target_status,
            acting_user_id=acting_user_id,
        )

    async def _record_transition_audit(
        self,
        entity_id: uuid.UUID,
        previous_status: OrderStatus,
        new_status: OrderStatus,
        acting_user_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Record a status transition in the audit trail.

        Args:
            entity_id: The order ID.
            previous_status: Status before the transition.
            new_status: Status after the transition.
            acting_user_id: The user who triggered the transition.
        """
        if self._audit_service is None:
            return

        await self._audit_service.log_action(
            action="ORDER_STATUS_TRANSITION",
            entity_type="sales_order",
            entity_id=entity_id,
            before_value={"status": previous_status.value},
            after_value={"status": new_status.value},
            extra={
                "source": "order_state_machine",
                "module": "sales",
                "summary": f"Order status changed from {previous_status.value} to {new_status.value}",
                "business_step": "Order workflow",
                "previous_status": previous_status.value,
                "new_status": new_status.value,
                "acting_user_id": str(acting_user_id) if acting_user_id else None,
                "transition_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
