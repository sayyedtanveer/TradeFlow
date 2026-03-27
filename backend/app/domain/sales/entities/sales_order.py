"""Sales Order Aggregate Root."""

from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from backend.app.domain.shared.base_entity import AggregateRoot
from backend.app.domain.sales.value_objects import OrderNumber, OrderStatus, PaymentStatus, Money


class SalesOrder(AggregateRoot):
    """
    Sales Order - Aggregate Root for order management.
    
    Responsibilities:
    - Order lifecycle management (status transitions)
    - Line items collection
    - Totals calculation and validation
    - Business rule enforcement
    """

    def __init__(
        self,
        id: UUID,
        tenant_id: UUID,
        order_number: OrderNumber,
        client_id: UUID,
        order_date: date,
        delivery_date: date,
    ):
        """Initialize Sales Order."""
        # AggregateRoot fields
        self.id = id
        self.tenant_id = tenant_id
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.is_active = True
        
        # Order identity
        self.order_number = order_number
        self.client_id = client_id
        self.order_date = order_date
        self.delivery_date = delivery_date
        
        # Status
        self.status = OrderStatus.DRAFT
        self.payment_status = PaymentStatus.PENDING
        
        # Totals (denormalized for efficiency)
        self.subtotal = Decimal("0")
        self.discount_amount = Decimal("0")
        self.tax_amount = Decimal("0")
        self.grand_total = Decimal("0")
        
        # Content
        self.lines: list = []  # List[SalesOrderLine]
        self.notes: str | None = None
        self.created_by: str | None = None
        
        self._validate()

    def _validate(self) -> None:
        """Validate order invariants."""
        if self.delivery_date < self.order_date:
            raise ValueError("Delivery date cannot be before order date")
        if not self.order_number:
            raise ValueError("Order number is required")

    def add_line(self, line) -> None:
        """
        Add a line to the order.
        
        Args:
            line: SalesOrderLine instance
            
        Raises:
            ValueError: If order not in DRAFT status
        """
        if self.status != OrderStatus.DRAFT:
            raise ValueError("Cannot add lines to non-draft orders")
        self.lines.append(line)
        self._recalculate_totals()

    def remove_line(self, line_id: UUID) -> None:
        """
        Remove a line from the order.
        
        Args:
            line_id: Line ID to remove
            
        Raises:
            ValueError: If order not in DRAFT status or line not found
        """
        if self.status != OrderStatus.DRAFT:
            raise ValueError("Cannot remove lines from non-draft orders")
        
        original_count = len(self.lines)
        self.lines = [line for line in self.lines if line.id != line_id]
        
        if len(self.lines) == original_count:
            raise ValueError(f"Line {line_id} not found")
        
        self._recalculate_totals()

    def apply_discount(self, discount_amount: Decimal) -> None:
        """
        Apply discount to order.
        
        Args:
            discount_amount: Discount amount
            
        Raises:
            ValueError: If discount exceeds subtotal or order not in DRAFT
        """
        if self.status != OrderStatus.DRAFT:
            raise ValueError("Cannot modify non-draft orders")
        
        discount_amount = Decimal(str(discount_amount))
        if discount_amount < 0:
            raise ValueError("Discount cannot be negative")
        if discount_amount > self.subtotal:
            raise ValueError("Discount cannot exceed subtotal")
        
        self.discount_amount = discount_amount
        self._recalculate_totals()

    def _recalculate_totals(self) -> None:
        """Recalculate order totals from lines."""
        from decimal import Decimal
        
        subtotal = Decimal("0")
        tax_total = Decimal("0")
        
        for line in self.lines:
            line._calculate_totals()  # Ensure line totals are fresh
            subtotal += line.quantity * line.unit_price
            tax_total += line.tax_amount
        
        self.subtotal = subtotal.quantize(Decimal("0.01"))
        self.tax_amount = tax_total.quantize(Decimal("0.01"))
        
        # Grand total = subtotal - discount + tax
        self.grand_total = (
            self.subtotal - self.discount_amount + self.tax_amount
        ).quantize(Decimal("0.01"))

    def can_transition_to(self, new_status: OrderStatus) -> bool:
        """
        Check if status transition is allowed.
        
        Valid transitions:
        - DRAFT → CONFIRMED, CANCELLED
        - CONFIRMED → PRODUCTION, READY, CANCELLED
        - PRODUCTION → READY, CANCELLED
        - READY → SHIPPED, CANCELLED
        - SHIPPED → DELIVERED, CANCELLED
        - DELIVERED → (no transitions)
        - CANCELLED → (final state)
        """
        valid_transitions = {
            OrderStatus.DRAFT: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
            OrderStatus.CONFIRMED: [OrderStatus.PRODUCTION, OrderStatus.READY, OrderStatus.CANCELLED],
            OrderStatus.PRODUCTION: [OrderStatus.READY, OrderStatus.CANCELLED],
            OrderStatus.READY: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
            OrderStatus.SHIPPED: [OrderStatus.DELIVERED, OrderStatus.CANCELLED],
            OrderStatus.DELIVERED: [],
            OrderStatus.CANCELLED: [],
        }
        return new_status in valid_transitions.get(self.status, [])

    def confirm(self) -> None:
        """
        Confirm order (transition from DRAFT → CONFIRMED).
        
        Raises:
            ValueError: If status transition invalid or order invalid
        """
        if not self.can_transition_to(OrderStatus.CONFIRMED):
            raise ValueError(
                f"Cannot confirm order in {self.status.value} status"
            )
        if not self.lines:
            raise ValueError("Cannot confirm order with no lines")
        
        self.status = OrderStatus.CONFIRMED
        self.updated_at = datetime.utcnow()

    def transition_to_production(self) -> None:
        """Transition order to PRODUCTION status."""
        if not self.can_transition_to(OrderStatus.PRODUCTION):
            raise ValueError(
                f"Cannot transition from {self.status.value} to PRODUCTION"
            )
        self.status = OrderStatus.PRODUCTION
        self.updated_at = datetime.utcnow()

    def transition_to_ready(self) -> None:
        """Transition order to READY status."""
        if not self.can_transition_to(OrderStatus.READY):
            raise ValueError(
                f"Cannot transition from {self.status.value} to READY"
            )
        self.status = OrderStatus.READY
        self.updated_at = datetime.utcnow()

    def ship(self) -> None:
        """Transition order to SHIPPED status."""
        if not self.can_transition_to(OrderStatus.SHIPPED):
            raise ValueError(
                f"Cannot transition from {self.status.value} to SHIPPED"
            )
        self.status = OrderStatus.SHIPPED
        self.updated_at = datetime.utcnow()

    def deliver(self) -> None:
        """Transition order to DELIVERED status."""
        if not self.can_transition_to(OrderStatus.DELIVERED):
            raise ValueError(
                f"Cannot transition from {self.status.value} to DELIVERED"
            )
        self.status = OrderStatus.DELIVERED
        self.updated_at = datetime.utcnow()

    def cancel(self) -> None:
        """Cancel order if allowed."""
        if not self.can_transition_to(OrderStatus.CANCELLED):
            raise ValueError(
                f"Cannot cancel order in {self.status.value} status"
            )
        self.status = OrderStatus.CANCELLED
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "order_number": str(self.order_number),
            "client_id": str(self.client_id),
            "order_date": self.order_date.isoformat(),
            "delivery_date": self.delivery_date.isoformat(),
            "status": self.status.value,
            "payment_status": self.payment_status.value,
            "subtotal": str(self.subtotal),
            "discount_amount": str(self.discount_amount),
            "tax_amount": str(self.tax_amount),
            "grand_total": str(self.grand_total),
            "lines": [line.to_dict() for line in self.lines],
            "notes": self.notes,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

