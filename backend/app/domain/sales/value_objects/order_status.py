"""Order and Payment Status Value Objects."""

from enum import Enum


class OrderStatus(str, Enum):
    """
    Order status lifecycle:
    DRAFT → CONFIRMED → PRODUCTION/READY → SHIPPED → DELIVERED
    
    Any state can transition to CANCELLED.
    """

    DRAFT = "draft"  # Initial state, not yet confirmed
    CONFIRMED = "confirmed"  # Credit & inventory verified, allocated
    PRODUCTION = "production"  # Partially in production (backorder exists)
    READY = "ready"  # Fully allocated, ready to ship
    SHIPPED = "shipped"  # Partial or full shipment sent
    DELIVERED = "delivered"  # Received by client
    CANCELLED = "cancelled"  # Cancelled (reverses allocations)

    def can_transition_to(self, target: "OrderStatus") -> bool:
        """
        Validate allowed state transitions.
        
        Args:
            target: Target OrderStatus
            
        Returns:
            True if transition is allowed
        """
        allowed = {
            OrderStatus.DRAFT: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
            OrderStatus.CONFIRMED: [
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
            OrderStatus.SHIPPED: [OrderStatus.DELIVERED, OrderStatus.CANCELLED],
            OrderStatus.DELIVERED: [OrderStatus.CANCELLED],
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
