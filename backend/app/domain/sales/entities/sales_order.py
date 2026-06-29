"""Sales Order Aggregate Root."""

from datetime import datetime, date, timezone
from decimal import Decimal
from uuid import UUID

from backend.app.domain.shared.base_entity import AggregateRoot
from backend.app.domain.sales.value_objects import OrderNumber, OrderStatus, PaymentStatus, Money


def _coerce_order_status(status: OrderStatus | str) -> OrderStatus:
    """Coerce a string or OrderStatus into a valid OrderStatus enum member."""
    if isinstance(status, OrderStatus):
        return status
    status_text = str(status).upper()
    # Try direct member lookup first, then by value
    member = OrderStatus.__members__.get(status_text)
    if member is not None:
        return member
    try:
        return OrderStatus(status_text)
    except ValueError:
        # For backward compatibility with old manufacturing statuses,
        # map them to CANCELLED (they are legacy/invalid in the new workflow).
        return OrderStatus.CANCELLED


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
        order_number: OrderNumber | str,
        client_id: UUID,
        order_date: date | str,
        delivery_date: date | str,
        status: OrderStatus | str = OrderStatus.PENDING_INVENTORY_VALIDATION,
        payment_status: PaymentStatus | str = PaymentStatus.PENDING,
        subtotal: Decimal | int | float | str = Decimal("0"),
        discount_amount: Decimal | int | float | str = Decimal("0"),
        tax_amount: Decimal | int | float | str = Decimal("0"),
        grand_total: Decimal | int | float | str = Decimal("0"),
        notes: str | None = None,
        created_by: str | None = None,
        approver_id: UUID | None = None,
        submitted_at: datetime | None = None,
        approved_at: datetime | None = None,
        rejected_at: datetime | None = None,
        approval_notes: str | None = None,
        lines: list | None = None,
        is_active: bool = True,
        is_deleted: bool = False,
        deleted_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        # Distribution workflow fields
        assigned_warehouse_id: UUID | None = None,
        assigned_at: datetime | None = None,
        accepted_at: datetime | None = None,
        dispatched_at: datetime | None = None,
        hold_reason: str | None = None,
    ):
        """Initialize Sales Order."""
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            created_at=created_at,
            updated_at=updated_at,
            is_deleted=is_deleted,
            deleted_at=deleted_at,
        )

        # Order identity
        if isinstance(order_number, OrderNumber):
            self.order_number = order_number
        else:
            try:
                self.order_number = OrderNumber(order_number)
            except ValueError:
                # Older/demo rows may use business-friendly numbers outside the SO-* pattern.
                self.order_number = order_number
        self.client_id = client_id
        self.order_date = date.fromisoformat(order_date) if isinstance(order_date, str) else order_date
        self.delivery_date = date.fromisoformat(delivery_date) if isinstance(delivery_date, str) else delivery_date

        # Status
        self.status = _coerce_order_status(status)
        self.payment_status = (
            payment_status if isinstance(payment_status, PaymentStatus) else PaymentStatus(str(payment_status).lower())
        )

        # Totals (denormalized for efficiency)
        self.subtotal = Decimal(str(subtotal))
        self.discount_amount = Decimal(str(discount_amount))
        self.tax_amount = Decimal(str(tax_amount))
        self.grand_total = Decimal(str(grand_total))

        # Content
        self.lines: list = lines or []  # List[SalesOrderLine]
        self.notes = notes
        self.created_by = created_by
        self.approver_id = approver_id
        self.submitted_at = submitted_at
        self.approved_at = approved_at
        self.rejected_at = rejected_at
        self.approval_notes = approval_notes
        self.is_active = is_active

        # Distribution workflow fields
        self.assigned_warehouse_id = assigned_warehouse_id
        self.assigned_at = assigned_at
        self.accepted_at = accepted_at
        self.dispatched_at = dispatched_at
        self.hold_reason = hold_reason

        self._validate()

    def _validate(self) -> None:
        """Validate order invariants."""
        if self.delivery_date < self.order_date:
            raise ValueError("Delivery date cannot be before order date")
        if not self.order_number:
            raise ValueError("Order number is required")

    # ── Status Transitions ──────────────────────────────────────────────

    def can_transition_to(self, new_status: OrderStatus) -> bool:
        """Check if status transition is allowed according to the state machine."""
        return self.status.can_transition_to(new_status)

    def transition_to(self, new_status: OrderStatus) -> None:
        """
        Transition to a new status, validating the state machine rules.

        Raises:
            ValueError: If the transition is not allowed
        """
        from backend.app.domain.sales.value_objects import get_allowed_transitions

        if not self.can_transition_to(new_status):
            allowed = get_allowed_transitions(self.status)
            allowed_names = [s.value for s in allowed]
            raise ValueError(
                f"Cannot transition from {self.status.value} to {new_status.value}. "
                f"Allowed transitions: {allowed_names}"
            )
        self.status = new_status
        self._touch()

    def assign_to_warehouse(self, warehouse_id: UUID) -> None:
        """Assign order to a warehouse (transitions to ASSIGNED)."""
        self.transition_to(OrderStatus.ASSIGNED)
        self.assigned_warehouse_id = warehouse_id
        self.assigned_at = datetime.now(timezone.utc)

    def accept(self) -> None:
        """Warehouse user accepts the order."""
        self.transition_to(OrderStatus.ACCEPTED)
        self.accepted_at = datetime.now(timezone.utc)

    def start_picking(self) -> None:
        """Transition to PICKING status."""
        self.transition_to(OrderStatus.PICKING)

    def start_packing(self) -> None:
        """Transition to PACKING status."""
        self.transition_to(OrderStatus.PACKING)

    def mark_ready_for_dispatch(self) -> None:
        """Transition to READY_FOR_DISPATCH status."""
        self.transition_to(OrderStatus.READY_FOR_DISPATCH)

    def dispatch(self) -> None:
        """Dispatch the order."""
        self.transition_to(OrderStatus.DISPATCHED)
        self.dispatched_at = datetime.now(timezone.utc)

    def invoice(self) -> None:
        """Mark order as invoiced."""
        self.transition_to(OrderStatus.INVOICED)

    def place_on_hold(self, reason: str) -> None:
        """Place order on hold (from ASSIGNED or ACCEPTED)."""
        self.transition_to(OrderStatus.ON_HOLD)
        self.hold_reason = reason

    def release_hold(self) -> None:
        """Release hold (transitions back to ASSIGNED)."""
        self.transition_to(OrderStatus.ASSIGNED)
        self.hold_reason = None

    def cancel(self) -> None:
        """Cancel order if allowed."""
        self.transition_to(OrderStatus.CANCELLED)

    def decline(self) -> None:
        """Warehouse user declines the order (transitions to PENDING_MANUAL_ASSIGNMENT)."""
        self.transition_to(OrderStatus.PENDING_MANUAL_ASSIGNMENT)
        self.assigned_warehouse_id = None
        self.assigned_at = None

    # ── Line Item Management ──────────────────────────────────────────────

    def add_line(self, line) -> None:
        """
        Add a line to the order.

        Args:
            line: SalesOrderLine instance

        Raises:
            ValueError: If order not in PENDING_INVENTORY_VALIDATION status
        """
        if self.status != OrderStatus.PENDING_INVENTORY_VALIDATION:
            raise ValueError("Cannot add lines to orders that have entered the workflow")
        self.lines.append(line)
        self._recalculate_totals()

    def remove_line(self, line_id: UUID) -> None:
        """
        Remove a line from the order.

        Args:
            line_id: Line ID to remove

        Raises:
            ValueError: If order not in initial status or line not found
        """
        if self.status != OrderStatus.PENDING_INVENTORY_VALIDATION:
            raise ValueError("Cannot remove lines from orders that have entered the workflow")

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
            ValueError: If discount exceeds subtotal or order not in initial status
        """
        if self.status != OrderStatus.PENDING_INVENTORY_VALIDATION:
            raise ValueError("Cannot modify orders that have entered the workflow")

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

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "order_number": str(self.order_number),
            "client_id": str(self.client_id),
            "client_name": getattr(self, "client_name", None),
            "client_code": getattr(self, "client_code", None),
            "order_date": self.order_date.isoformat(),
            "delivery_date": self.delivery_date.isoformat(),
            "status": self.status.value,
            "payment_status": self.payment_status.name,
            "subtotal": str(self.subtotal),
            "discount_amount": str(self.discount_amount),
            "tax_amount": str(self.tax_amount),
            "grand_total": str(self.grand_total),
            "item_count": len(self.lines),
            "item_summary": getattr(self, "item_summary", None),
            "lines": [line.to_dict() for line in self.lines],
            "notes": self.notes,
            "created_by": self.created_by,
            "approver_id": str(self.approver_id) if self.approver_id else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "approval_notes": self.approval_notes,
            # Distribution workflow fields
            "assigned_warehouse_id": str(self.assigned_warehouse_id) if self.assigned_warehouse_id else None,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "dispatched_at": self.dispatched_at.isoformat() if self.dispatched_at else None,
            "hold_reason": self.hold_reason,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
