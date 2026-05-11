"""Inventory Reservation entity for tracking material reservations and lifecycle."""
from __future__ import annotations

import uuid
import enum
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional


class ReservationStatus(str, enum.Enum):
    RESERVED = "RESERVED"
    ISSUED = "ISSUED"
    CONSUMED = "CONSUMED"
    REJECTED = "REJECTED"
    RETURNED = "RETURNED"


class InventoryReservation:
    """Represents a material reservation with full lifecycle tracking."""

    def __init__(
        self,
        id: uuid.UUID,
        tenant_id: uuid.UUID,
        reference_type: str,  # "work_order", "sales_order", etc.
        reference_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        status: ReservationStatus,
        unit_id: Optional[uuid.UUID] = None,
        issued_quantity: Decimal = Decimal("0"),
        consumed_quantity: Decimal = Decimal("0"),
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.tenant_id = tenant_id
        self.reference_type = reference_type
        self.reference_id = reference_id
        self.material_id = material_id
        self.quantity = quantity
        self.status = status
        self.unit_id = unit_id
        self.issued_quantity = issued_quantity
        self.consumed_quantity = consumed_quantity
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def issue(self, quantity: Decimal) -> None:
        """Issue material from reservation."""
        if self.status != ReservationStatus.RESERVED:
            raise ValueError(f"Cannot issue reservation in {self.status} status")

        if quantity > (self.quantity - self.issued_quantity):
            raise ValueError(
                f"Cannot issue {quantity}: only {self.quantity - self.issued_quantity} available in reservation"
            )

        self.issued_quantity += quantity
        if self.issued_quantity >= self.quantity:
            self.status = ReservationStatus.ISSUED

        self.updated_at = datetime.now(timezone.utc)

    def consume(self, quantity: Decimal) -> None:
        """Consume material from reservation (during production)."""
        if self.status not in (ReservationStatus.ISSUED, ReservationStatus.RESERVED):
            raise ValueError(f"Cannot consume reservation in {self.status} status")

        if quantity > (self.issued_quantity - self.consumed_quantity):
            raise ValueError(
                f"Cannot consume {quantity}: only {self.issued_quantity - self.consumed_quantity} issued"
            )

        self.consumed_quantity += quantity
        if self.consumed_quantity >= self.quantity:
            self.status = ReservationStatus.CONSUMED

        self.updated_at = datetime.now(timezone.utc)

    def reject(self, quantity: Decimal) -> None:
        """Reject material from reservation (QC rejection)."""
        if quantity > self.issued_quantity:
            raise ValueError(
                f"Cannot reject {quantity}: only {self.issued_quantity} issued"
            )

        self.issued_quantity -= quantity
        self.status = ReservationStatus.REJECTED
        self.updated_at = datetime.now(timezone.utc)

    def return_material(self, quantity: Decimal) -> None:
        """Return material to inventory (partial return)."""
        if quantity > self.issued_quantity:
            raise ValueError(
                f"Cannot return {quantity}: only {self.issued_quantity} issued"
            )

        self.issued_quantity -= quantity
        self.status = ReservationStatus.RETURNED
        self.updated_at = datetime.now(timezone.utc)

    @property
    def remaining_quantity(self) -> Decimal:
        """Calculate remaining quantity to be issued."""
        return self.quantity - self.issued_quantity

    @property
    def is_fully_issued(self) -> bool:
        """Check if reservation is fully issued."""
        return self.issued_quantity >= self.quantity
