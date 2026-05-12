"""Order and Payment Status Value Objects."""

from enum import Enum


class OrderStatus(str, Enum):
    """
    Order status lifecycle:
    DRAFT → PENDING_APPROVAL → APPROVED → WORK_ORDER_CREATED → CONFIRMED → 
    PRODUCTION → READY → READY_FOR_DISPATCH → SHIPPED → DELIVERED → INVOICED → PAYMENT_RECEIVED → COMPLETED
    
    Any state can transition to CANCELLED.
    """

    DRAFT = "DRAFT"  # Initial state, editable before submission
    PENDING_APPROVAL = "PENDING_APPROVAL"  # Waiting for manager review
    APPROVED = "APPROVED"  # Manager approved the order
    REJECTED = "REJECTED"  # Manager rejected the order
    WORK_ORDER_CREATED = "WORK_ORDER_CREATED"  # Work order created from sales order
    CONFIRMED = "CONFIRMED"  # Credit & inventory verified, allocated
    PROCESSING = "PROCESSING"  # Execution in progress
    PRODUCTION = "PRODUCTION"  # Partially in production (backorder exists)
    READY = "READY"  # Fully allocated, ready to ship
    READY_FOR_DISPATCH = "READY_FOR_DISPATCH"  # Finished goods ready for dispatch
    SHIPPED = "SHIPPED"  # Partial or full shipment sent
    DELIVERED = "DELIVERED"  # Received by client
    INVOICED = "INVOICED"  # Invoice generated and sent
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"  # Payment received
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
                OrderStatus.WORK_ORDER_CREATED,
                OrderStatus.CONFIRMED,
                OrderStatus.PROCESSING,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.REJECTED: [],
            OrderStatus.WORK_ORDER_CREATED: [
                OrderStatus.CONFIRMED,
                OrderStatus.PROCESSING,
                OrderStatus.PRODUCTION,
                OrderStatus.CANCELLED,
            ],
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
                OrderStatus.READY_FOR_DISPATCH,
                OrderStatus.SHIPPED,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.READY: [
                OrderStatus.READY_FOR_DISPATCH,
                OrderStatus.SHIPPED,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.READY_FOR_DISPATCH: [
                OrderStatus.SHIPPED,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.SHIPPED: [
                OrderStatus.DELIVERED,
                OrderStatus.INVOICED,
                OrderStatus.COMPLETED,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.DELIVERED: [
                OrderStatus.INVOICED,
                OrderStatus.COMPLETED,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.INVOICED: [
                OrderStatus.PAYMENT_RECEIVED,
                OrderStatus.COMPLETED,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.PAYMENT_RECEIVED: [
                OrderStatus.COMPLETED,
            ],
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
