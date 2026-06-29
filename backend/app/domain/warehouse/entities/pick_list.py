"""PickList and PickListLine domain entities for warehouse fulfilment."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from backend.app.domain.shared.base_entity import AggregateRoot, BaseEntity


class PickListStatus(str, Enum):
    """Status of a pick list in the fulfilment workflow."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class PickListLine(BaseEntity):
    """
    Individual item to pick for an order.

    Tracks the product, required quantity, and picking progress.
    """

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        pick_list_id: Optional[uuid.UUID] = None,
        order_line_id: uuid.UUID,
        product_id: uuid.UUID,
        product_name: str,
        sku: str,
        quantity: int,
        storage_location: Optional[str] = None,
        is_picked: bool = False,
        picked_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        is_deleted: bool = False,
        deleted_at: Optional[datetime] = None,
    ) -> None:
        """Initialize PickListLine."""
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            created_at=created_at,
            updated_at=updated_at,
            is_deleted=is_deleted,
            deleted_at=deleted_at,
        )
        self._pick_list_id = pick_list_id
        self._order_line_id = order_line_id
        self._product_id = product_id
        self._product_name = product_name
        self._sku = sku
        self._quantity = quantity
        self._storage_location = storage_location
        self._is_picked = is_picked
        self._picked_at = picked_at

        self._validate()

    def _validate(self) -> None:
        """Validate pick list line invariants."""
        if not self._order_line_id:
            raise ValueError("Order line ID is required")
        if not self._product_id:
            raise ValueError("Product ID is required")
        if not self._product_name:
            raise ValueError("Product name is required")
        if not self._sku:
            raise ValueError("SKU is required")
        if self._quantity <= 0:
            raise ValueError("Quantity must be greater than zero")

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def pick_list_id(self) -> Optional[uuid.UUID]:
        return self._pick_list_id

    @pick_list_id.setter
    def pick_list_id(self, value: uuid.UUID) -> None:
        self._pick_list_id = value

    @property
    def order_line_id(self) -> uuid.UUID:
        return self._order_line_id

    @property
    def product_id(self) -> uuid.UUID:
        return self._product_id

    @property
    def product_name(self) -> str:
        return self._product_name

    @property
    def sku(self) -> str:
        return self._sku

    @property
    def quantity(self) -> int:
        return self._quantity

    @property
    def storage_location(self) -> Optional[str]:
        return self._storage_location

    @property
    def is_picked(self) -> bool:
        return self._is_picked

    @property
    def picked_at(self) -> Optional[datetime]:
        return self._picked_at

    # ── Domain Operations ─────────────────────────────────────────────────

    def mark_as_picked(self) -> None:
        """Mark this line item as picked."""
        if self._is_picked:
            raise ValueError("Item is already picked")
        self._is_picked = True
        self._picked_at = datetime.now(timezone.utc)
        self._touch()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "pick_list_id": str(self._pick_list_id) if self._pick_list_id else None,
            "order_line_id": str(self._order_line_id),
            "product_id": str(self._product_id),
            "product_name": self._product_name,
            "sku": self._sku,
            "quantity": self._quantity,
            "storage_location": self._storage_location,
            "is_picked": self._is_picked,
            "picked_at": self._picked_at.isoformat() if self._picked_at else None,
        }


class PickList(AggregateRoot):
    """
    Pick List Aggregate Root — generated when a warehouse user accepts an order.

    Contains the list of items to be physically picked from warehouse locations
    for a given sales order.

    Business rules:
    - A pick list is generated automatically upon order acceptance (ASSIGNED → ACCEPTED)
    - Contains exactly the products, SKUs, quantities from the order's line items
    - Tracks picking progress per line
    - Transitions: PENDING → IN_PROGRESS (first item picked) → COMPLETED (all items picked)
    """

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        order_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        status: PickListStatus = PickListStatus.PENDING,
        lines: Optional[List[PickListLine]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        is_deleted: bool = False,
        deleted_at: Optional[datetime] = None,
    ) -> None:
        """Initialize PickList aggregate root."""
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            created_at=created_at,
            updated_at=updated_at,
            is_deleted=is_deleted,
            deleted_at=deleted_at,
        )
        self._order_id = order_id
        self._warehouse_id = warehouse_id
        self._status = status
        self._lines: List[PickListLine] = lines or []
        self._completed_at = completed_at

        self._validate()

    def _validate(self) -> None:
        """Validate pick list invariants."""
        if not self._order_id:
            raise ValueError("Order ID is required")
        if not self._warehouse_id:
            raise ValueError("Warehouse ID is required")

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def order_id(self) -> uuid.UUID:
        return self._order_id

    @property
    def warehouse_id(self) -> uuid.UUID:
        return self._warehouse_id

    @property
    def status(self) -> PickListStatus:
        return self._status

    @property
    def lines(self) -> List[PickListLine]:
        return list(self._lines)

    @property
    def completed_at(self) -> Optional[datetime]:
        return self._completed_at

    @property
    def total_items(self) -> int:
        """Total number of line items to pick."""
        return len(self._lines)

    @property
    def picked_items(self) -> int:
        """Number of items already picked."""
        return sum(1 for line in self._lines if line.is_picked)

    @property
    def is_fully_picked(self) -> bool:
        """Whether all line items have been picked."""
        return self.total_items > 0 and self.picked_items == self.total_items

    # ── Domain Operations ─────────────────────────────────────────────────

    def add_line(self, line: PickListLine) -> None:
        """Add a line item to the pick list."""
        line.pick_list_id = self.id
        self._lines.append(line)
        self._touch()

    def start_picking(self) -> None:
        """Transition to IN_PROGRESS when picking begins."""
        if self._status != PickListStatus.PENDING:
            raise ValueError(
                f"Cannot start picking from status {self._status.value}. "
                "Pick list must be in PENDING status."
            )
        self._status = PickListStatus.IN_PROGRESS
        self._touch()

    def mark_item_picked(self, line_id: uuid.UUID) -> None:
        """Mark a specific line item as picked."""
        line = next((l for l in self._lines if l.id == line_id), None)
        if line is None:
            raise ValueError(f"Pick list line {line_id} not found")

        # Auto-transition to IN_PROGRESS on first pick
        if self._status == PickListStatus.PENDING:
            self._status = PickListStatus.IN_PROGRESS

        line.mark_as_picked()

        # Auto-complete if all items are now picked
        if self.is_fully_picked:
            self._status = PickListStatus.COMPLETED
            self._completed_at = datetime.now(timezone.utc)

        self._touch()

    def complete(self) -> None:
        """Mark the pick list as completed."""
        if not self.is_fully_picked:
            unpicked = self.total_items - self.picked_items
            raise ValueError(
                f"Cannot complete pick list: {unpicked} items remain unpicked"
            )
        self._status = PickListStatus.COMPLETED
        self._completed_at = datetime.now(timezone.utc)
        self._touch()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "order_id": str(self._order_id),
            "warehouse_id": str(self._warehouse_id),
            "status": self._status.value,
            "total_items": self.total_items,
            "picked_items": self.picked_items,
            "lines": [line.to_dict() for line in self._lines],
            "created_at": self.created_at.isoformat(),
            "completed_at": self._completed_at.isoformat() if self._completed_at else None,
        }
