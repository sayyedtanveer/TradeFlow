"""Order and Payment Status Value Objects."""

from enum import Enum


class OrderStatus(str, Enum):
    """
    TradeFlow distribution order lifecycle.

    State machine:
    PENDING_INVENTORY_VALIDATION → ASSIGNED / PENDING_MANUAL_ASSIGNMENT / CANCELLED
    PENDING_MANUAL_ASSIGNMENT → ASSIGNED / CANCELLED
    ASSIGNED → ACCEPTED / PENDING_MANUAL_ASSIGNMENT / ON_HOLD / CANCELLED
    ACCEPTED → PICKING / ON_HOLD
    PICKING → PACKING
    PACKING → READY_FOR_DISPATCH
    READY_FOR_DISPATCH → DISPATCHED
    DISPATCHED → INVOICED
    ON_HOLD → ASSIGNED
    INVOICED → (terminal)
    CANCELLED → (terminal)
    """

    PENDING_INVENTORY_VALIDATION = "PENDING_INVENTORY_VALIDATION"
    PENDING_MANUAL_ASSIGNMENT = "PENDING_MANUAL_ASSIGNMENT"
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    PICKING = "PICKING"
    PACKING = "PACKING"
    READY_FOR_DISPATCH = "READY_FOR_DISPATCH"
    DISPATCHED = "DISPATCHED"
    INVOICED = "INVOICED"
    ON_HOLD = "ON_HOLD"
    CANCELLED = "CANCELLED"

    def can_transition_to(self, target: "OrderStatus") -> bool:
        """
        Validate allowed state transitions.

        Args:
            target: Target OrderStatus

        Returns:
            True if transition is allowed
        """
        return target in ORDER_STATUS_TRANSITIONS.get(self, [])


# Allowed transitions map — the single source of truth for the order state machine.
ORDER_STATUS_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
    OrderStatus.PENDING_INVENTORY_VALIDATION: [
        OrderStatus.ASSIGNED,
        OrderStatus.PENDING_MANUAL_ASSIGNMENT,
        OrderStatus.CANCELLED,
    ],
    OrderStatus.PENDING_MANUAL_ASSIGNMENT: [
        OrderStatus.ASSIGNED,
        OrderStatus.CANCELLED,
    ],
    OrderStatus.ASSIGNED: [
        OrderStatus.ACCEPTED,
        OrderStatus.PENDING_MANUAL_ASSIGNMENT,
        OrderStatus.ON_HOLD,
        OrderStatus.CANCELLED,
    ],
    OrderStatus.ACCEPTED: [
        OrderStatus.PICKING,
        OrderStatus.ON_HOLD,
    ],
    OrderStatus.PICKING: [
        OrderStatus.PACKING,
    ],
    OrderStatus.PACKING: [
        OrderStatus.READY_FOR_DISPATCH,
    ],
    OrderStatus.READY_FOR_DISPATCH: [
        OrderStatus.DISPATCHED,
    ],
    OrderStatus.DISPATCHED: [
        OrderStatus.INVOICED,
    ],
    OrderStatus.INVOICED: [],
    OrderStatus.ON_HOLD: [
        OrderStatus.ASSIGNED,
    ],
    OrderStatus.CANCELLED: [],
}


def get_allowed_transitions(status: OrderStatus) -> list[OrderStatus]:
    """Return the list of valid next statuses from the given status."""
    return ORDER_STATUS_TRANSITIONS.get(status, [])


class PaymentStatus(str, Enum):
    """Payment status for orders."""

    PENDING = "pending"  # No payment received
    PARTIAL = "partial"  # Partial payment received
    PAID = "paid"  # Full payment received


class LineStatus(str, Enum):
    """Individual line status within an order."""

    PENDING = "pending"  # Awaiting allocation
    ALLOCATED = "allocated"  # Stock allocated
    BACKORDER = "backorder"  # Shortage, awaiting stock
    SHIPPED = "shipped"  # Partially or fully shipped
    DELIVERED = "delivered"  # Received
    CANCELLED = "cancelled"
