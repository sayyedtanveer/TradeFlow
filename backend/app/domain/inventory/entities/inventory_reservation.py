"""Inventory Reservation entity for tracking material reservations and lifecycle.

Implements the inventory reservation system for sales orders:
- Reserves ordered quantities upon order confirmation to prevent overselling
- Releases reservations on order cancellation
- Available quantity = current_stock - reserved_quantity

Requirements: 5.7, 6.3, 6.13
"""
from __future__ import annotations

import uuid
import enum
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional


class ReservationStatus(str, enum.Enum):
    RESERVED = "RESERVED"
    PARTIALLY_ISSUED = "PARTIALLY_ISSUED"
    ISSUED = "ISSUED"
    PARTIALLY_CONSUMED = "PARTIALLY_CONSUMED"
    CONSUMED = "CONSUMED"
    REJECTED = "REJECTED"
    RETURNED = "RETURNED"
    RELEASED = "RELEASED"


class InventoryReservation:
    """Represents a material reservation with full lifecycle tracking.

    A reservation earmarks inventory for a specific sales order line to prevent
    overselling. Reservations are warehouse-scoped when a warehouse is assigned.
    """

    def __init__(
        self,
        id: uuid.UUID,
        tenant_id: uuid.UUID,
        reference_type: str,  # "sales_order_line", "purchase_order", etc.
        reference_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        status: ReservationStatus,
        unit_id: Optional[uuid.UUID] = None,
        batch_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        order_id: Optional[uuid.UUID] = None,
        issued_quantity: Decimal = Decimal("0"),
        consumed_quantity: Decimal = Decimal("0"),
        returned_quantity: Decimal = Decimal("0"),
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
        self.batch_id = batch_id
        self.warehouse_id = warehouse_id
        self.order_id = order_id
        self.issued_quantity = issued_quantity
        self.consumed_quantity = consumed_quantity
        self.returned_quantity = returned_quantity
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def issue(self, quantity: Decimal) -> None:
        """Issue material from reservation."""
        if self.status not in (ReservationStatus.RESERVED, ReservationStatus.PARTIALLY_ISSUED):
            raise ValueError(f"Cannot issue reservation in {self.status} status")

        if quantity > (self.quantity - self.issued_quantity):
            raise ValueError(
                f"Cannot issue {quantity}: only {self.quantity - self.issued_quantity} available in reservation"
            )

        self.issued_quantity += quantity
        if self.issued_quantity >= self.quantity:
            self.status = ReservationStatus.ISSUED
        else:
            self.status = ReservationStatus.PARTIALLY_ISSUED

        self.updated_at = datetime.now(timezone.utc)

    def consume(self, quantity: Decimal) -> None:
        """Consume material from reservation (during fulfilment)."""
        if self.status not in (
            ReservationStatus.ISSUED,
            ReservationStatus.PARTIALLY_ISSUED,
            ReservationStatus.PARTIALLY_CONSUMED,
        ):
            raise ValueError(f"Cannot consume reservation in {self.status} status")

        if quantity > (self.issued_quantity - self.consumed_quantity - self.returned_quantity):
            raise ValueError(
                "Cannot consume "
                f"{quantity}: only {self.issued_quantity - self.consumed_quantity - self.returned_quantity} issued"
            )

        self.consumed_quantity += quantity
        if self.consumed_quantity >= self.quantity:
            self.status = ReservationStatus.CONSUMED
        else:
            self.status = ReservationStatus.PARTIALLY_CONSUMED

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
        if quantity > (self.issued_quantity - self.consumed_quantity - self.returned_quantity):
            raise ValueError(
                "Cannot return "
                f"{quantity}: only {self.issued_quantity - self.consumed_quantity - self.returned_quantity} returnable"
            )

        self.returned_quantity += quantity
        self.status = (
            ReservationStatus.RETURNED
            if self.consumed_quantity == Decimal("0")
            else ReservationStatus.PARTIALLY_CONSUMED
        )
        self.updated_at = datetime.now(timezone.utc)

    @property
    def remaining_quantity(self) -> Decimal:
        """Calculate remaining quantity to be issued."""
        return self.quantity - self.issued_quantity

    @property
    def is_fully_issued(self) -> bool:
        """Check if reservation is fully issued."""
        return self.issued_quantity >= self.quantity

    def release(self) -> None:
        """Release the reservation (e.g., on order cancellation).

        Transitions to RELEASED status, making the reserved quantity
        available for other orders.
        """
        if self.status == ReservationStatus.RELEASED:
            return  # Already released, idempotent
        if self.status in (ReservationStatus.CONSUMED, ReservationStatus.ISSUED):
            raise ValueError(
                f"Cannot release reservation in {self.status} status — "
                "stock has already been issued/consumed"
            )
        self.status = ReservationStatus.RELEASED
        self.updated_at = datetime.now(timezone.utc)

    @property
    def is_active(self) -> bool:
        """Check if this reservation is still holding stock."""
        return self.status in (
            ReservationStatus.RESERVED,
            ReservationStatus.PARTIALLY_ISSUED,
        )
