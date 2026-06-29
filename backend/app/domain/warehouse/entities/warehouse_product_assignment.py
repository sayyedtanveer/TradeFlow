"""Warehouse-Product Assignment Entity."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from backend.app.domain.shared.base_entity import BaseEntity


class WarehouseProductAssignment(BaseEntity):
    """
    Warehouse-Product Assignment - Entity for managing which warehouses carry which products.

    Responsibilities:
    - Track product availability per warehouse
    - Store default reorder levels per warehouse-product combo
    - Support querying available warehouses for a product
    """

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        warehouse_id: uuid.UUID,
        product_id: uuid.UUID,
        is_available: bool = True,
        default_reorder_level: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        is_deleted: bool = False,
        deleted_at: Optional[datetime] = None,
    ) -> None:
        """Initialize Warehouse-Product Assignment entity."""
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            created_at=created_at,
            updated_at=updated_at,
            is_deleted=is_deleted,
            deleted_at=deleted_at,
        )
        self._warehouse_id = warehouse_id
        self._product_id = product_id
        self._is_available = is_available
        self._default_reorder_level = default_reorder_level

        self._validate()

    def _validate(self) -> None:
        """Validate assignment invariants."""
        if not self._warehouse_id:
            raise ValueError("Warehouse ID is required")
        if not self._product_id:
            raise ValueError("Product ID is required")
        if self._default_reorder_level < 0:
            raise ValueError("Default reorder level cannot be negative")

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def warehouse_id(self) -> uuid.UUID:
        return self._warehouse_id

    @property
    def product_id(self) -> uuid.UUID:
        return self._product_id

    @property
    def is_available(self) -> bool:
        return self._is_available

    @is_available.setter
    def is_available(self, value: bool) -> None:
        self._is_available = value

    @property
    def default_reorder_level(self) -> int:
        return self._default_reorder_level

    @default_reorder_level.setter
    def default_reorder_level(self, value: int) -> None:
        if value < 0:
            raise ValueError("Default reorder level cannot be negative")
        self._default_reorder_level = value

    # ── Business Methods ──────────────────────────────────────────────────

    def mark_unavailable(self) -> None:
        """Mark product as unavailable in this warehouse."""
        self._is_available = False

    def mark_available(self) -> None:
        """Mark product as available in this warehouse."""
        self._is_available = True
