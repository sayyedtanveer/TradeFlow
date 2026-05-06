"""
Work Order domain entity with lifecycle state machine.

Valid transitions:
    PLANNED → RELEASED → IN_PROGRESS → COMPLETED → CLOSED
"""
from __future__ import annotations

import uuid
import enum
from datetime import date, datetime, timezone
from typing import Optional
from decimal import Decimal


class WorkOrderStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    RELEASED = "RELEASED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"


class WorkOrderPriority(str, enum.Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


# Allowed status transitions
_TRANSITIONS: dict[WorkOrderStatus, set[WorkOrderStatus]] = {
    WorkOrderStatus.PLANNED:     {WorkOrderStatus.RELEASED},
    WorkOrderStatus.RELEASED:    {WorkOrderStatus.IN_PROGRESS},
    WorkOrderStatus.IN_PROGRESS: {WorkOrderStatus.COMPLETED},
    WorkOrderStatus.COMPLETED:   {WorkOrderStatus.CLOSED},
    WorkOrderStatus.CLOSED:      set(),
}


class InvalidStatusTransitionError(Exception):
    """Raised when a lifecycle transition is not permitted."""
    error_code = "INVALID_STATUS_TRANSITION"


class WorkOrderImmutableError(Exception):
    """Raised when a locked field is edited after WO is released."""
    error_code = "WO_IMMUTABLE"


class WorkOrder:
    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: uuid.UUID,
        wo_number: str,
        product_id: uuid.UUID,
        bom_id: uuid.UUID,
        planned_quantity: Decimal,
        start_date: date,
        due_date: date,
        created_by: uuid.UUID,
        status: WorkOrderStatus = WorkOrderStatus.PLANNED,
        priority: WorkOrderPriority = WorkOrderPriority.NORMAL,
        produced_quantity: Decimal = Decimal("0"),
        scrap_quantity: Decimal = Decimal("0"),
        sales_order_id: Optional[uuid.UUID] = None,
        sales_order_line_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
        is_deleted: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id or uuid.uuid4()
        self.tenant_id = tenant_id
        self.wo_number = wo_number
        self.product_id = product_id
        self.bom_id = bom_id
        self.planned_quantity = planned_quantity
        self.start_date = start_date
        self.due_date = due_date
        self.created_by = created_by
        self.status = status
        self.priority = priority
        self.produced_quantity = produced_quantity
        self.scrap_quantity = scrap_quantity
        self.sales_order_id = sales_order_id
        self.sales_order_line_id = sales_order_line_id
        self.notes = notes
        self.is_deleted = is_deleted
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    # ── Lifecycle guards ────────────────────────────────────────────────────────

    def _transition_to(self, new_status: WorkOrderStatus) -> None:
        allowed = _TRANSITIONS[self.status]
        if new_status not in allowed:
            raise InvalidStatusTransitionError(
                f"Cannot transition from {self.status} to {new_status}. "
                f"Allowed: {[s.value for s in allowed] or 'none'}"
            )
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)

    def release(self) -> None:
        """PLANNED → RELEASED. Locks immutable fields."""
        self._transition_to(WorkOrderStatus.RELEASED)

    def start(self) -> None:
        """RELEASED → IN_PROGRESS."""
        self._transition_to(WorkOrderStatus.IN_PROGRESS)

    def complete(self) -> None:
        """IN_PROGRESS → COMPLETED. Requires produced_quantity > 0."""
        from backend.app.domain.manufacturing.exceptions import MaterialNotIssuedError
        if self.produced_quantity <= 0:
            raise MaterialNotIssuedError("Cannot complete: no production has been recorded.")
        self._transition_to(WorkOrderStatus.COMPLETED)

    def close(self) -> None:
        """COMPLETED → CLOSED."""
        self._transition_to(WorkOrderStatus.CLOSED)

    # ── Immutability guard ──────────────────────────────────────────────────────

    @property
    def is_locked(self) -> bool:
        """Once released, core fields cannot be edited."""
        return self.status not in (WorkOrderStatus.PLANNED,)

    def update_quantities(self, produced: Decimal, scrap: Decimal) -> None:
        self.produced_quantity = produced
        self.scrap_quantity = scrap
        self.updated_at = datetime.now(timezone.utc)
