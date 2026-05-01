"""Order and Payment Status Value Objects."""

from enum import Enum


class OrderStatus(str, Enum):
    """
    Order status lifecycle:
    DRAFT → CONFIRMED → PRODUCTION/READY → SHIPPED → DELIVERED
    
    Any state can transition to CANCELLED.
    """

    DRAFT = "DRAFT"  # Initial state, editable before submission
    PENDING_APPROVAL = "PENDING_APPROVAL"  # Waiting for manager review
    APPROVED = "APPROVED"  # Approved and ready for execution
    REJECTED = "REJECTED"  # Manager rejected the order
    CONFIRMED = "CONFIRMED"  # Credit & inventory verified, allocated
    PROCESSING = "PROCESSING"  # Execution in progress
    PRODUCTION = "PRODUCTION"  # Partially in production (backorder exists)
    READY = "READY"  # Fully allocated, ready to ship
    SHIPPED = "SHIPPED"  # Partial or full shipment sent
    DELIVERED = "DELIVERED"  # Received by client
    COMPLETED = "COMPLETED"  # Commercially completed
    CANCELLED = "CANCELLED"  # Cancelled (reverses allocations)

    def can_transition_to(self, target: "OrderStatus") -> bool:
        """
        Validate allowed state transitions.
        
        Args:
            target: Target OrderStatus
            
        Returns:
            True if transition is allowed
        """
        allowed = {
            OrderStatus.DRAFT: [
                OrderStatus.PENDING_APPROVAL,
                OrderStatus.CONFIRMED,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.PENDING_APPROVAL: [
                OrderStatus.APPROVED,
                OrderStatus.REJECTED,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.APPROVED: [
                OrderStatus.CONFIRMED,
                OrderStatus.PROCESSING,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.REJECTED: [],
            OrderStatus.CONFIRMED: [
                OrderStatus.PROCESSING,
                OrderStatus.PRODUCTION,
                OrderStatus.READY,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.PROCESSING: [
                OrderStatus.PRODUCTION,
                OrderStatus.READY,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.PRODUCTION: [
                OrderStatus.READY,
                OrderStatus.SHIPPED,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.READY: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
            OrderStatus.SHIPPED: [
                OrderStatus.DELIVERED,
                OrderStatus.COMPLETED,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.DELIVERED: [OrderStatus.COMPLETED, OrderStatus.CANCELLED],
            OrderStatus.COMPLETED: [],
            OrderStatus.CANCELLED: [],
        }
        return target in allowed.get(self, [])


class PaymentStatus(str, Enum):
    """Payment status for orders."""

    PENDING = "pending"  # No payment received
    PARTIAL = "partial"  # Partial payment received
    PAID = "paid"  # Full payment received


class LineStatus(str, Enum):
    """Individual line status within an order."""

    PENDING = "pending"  # Awaiting allocation
    ALLOCATED = "allocated"  # Stock allocated or work order created
    BACKORDER = "backorder"  # Shortage, work order in progress
    SHIPPED = "shipped"  # Partially or fully shipped
    DELIVERED = "delivered"  # Received
    CANCELLED = "cancelled"
