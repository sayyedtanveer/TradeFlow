"""Warehouse Product Threshold Entity."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from backend.app.domain.shared.base_entity import BaseEntity


class WarehouseProductThreshold(BaseEntity):
    """
    Per-warehouse, per-product reorder threshold configuration.

    Used by the low-stock notification system to determine when
    stock levels have fallen below acceptable limits.
    """

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        warehouse_id: uuid.UUID,
        product_id: uuid.UUID,
        reorder_threshold: int,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        is_deleted: bool = False,
        deleted_at: Optional[datetime] = None,
    ) -> None:
        """Initialize WarehouseProductThreshold."""
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
        self._reorder_threshold = reorder_threshold

        self._validate()

    def _validate(self) -> None:
        """Validate threshold invariants."""
        if not self._warehouse_id:
            raise ValueError("Warehouse ID is required")
        if not self._product_id:
            raise ValueError("Product ID is required")
        if self._reorder_threshold < 0:
            raise ValueError("Reorder threshold cannot be negative")

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def warehouse_id(self) -> uuid.UUID:
        return self._warehouse_id

    @property
    def product_id(self) -> uuid.UUID:
        return self._product_id

    @property
    def reorder_threshold(self) -> int:
        return self._reorder_threshold

    @reorder_threshold.setter
    def reorder_threshold(self, value: int) -> None:
        if value < 0:
            raise ValueError("Reorder threshold cannot be negative")
        self._reorder_threshold = value
        self._touch()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "warehouse_id": str(self._warehouse_id),
            "product_id": str(self._product_id),
            "reorder_threshold": self._reorder_threshold,
        }
