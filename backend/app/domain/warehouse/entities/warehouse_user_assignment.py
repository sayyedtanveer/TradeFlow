"""Warehouse User Assignment Entity."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.app.domain.shared.base_entity import BaseEntity


class WarehouseUserAssignment(BaseEntity):
    """
    Represents the assignment of a user to a warehouse.

    Business rules:
    - A user can only be assigned to ONE warehouse at a time (enforced at repository level)
    - Reassigning a user to a different warehouse revokes the previous assignment
    - Tracks who performed the assignment for audit purposes
    """

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        user_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        assigned_at: Optional[datetime] = None,
        assigned_by: Optional[uuid.UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        is_deleted: bool = False,
        deleted_at: Optional[datetime] = None,
    ) -> None:
        """Initialize WarehouseUserAssignment."""
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            created_at=created_at,
            updated_at=updated_at,
            is_deleted=is_deleted,
            deleted_at=deleted_at,
        )
        self._user_id = user_id
        self._warehouse_id = warehouse_id
        self._assigned_at = assigned_at or datetime.now(timezone.utc)
        self._assigned_by = assigned_by

        self._validate()

    def _validate(self) -> None:
        """Validate assignment invariants."""
        if not self._user_id:
            raise ValueError("User ID is required")
        if not self._warehouse_id:
            raise ValueError("Warehouse ID is required")

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def user_id(self) -> uuid.UUID:
        return self._user_id

    @property
    def warehouse_id(self) -> uuid.UUID:
        return self._warehouse_id

    @property
    def assigned_at(self) -> datetime:
        return self._assigned_at

    @property
    def assigned_by(self) -> Optional[uuid.UUID]:
        return self._assigned_by

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "user_id": str(self._user_id),
            "warehouse_id": str(self._warehouse_id),
            "assigned_at": self._assigned_at.isoformat(),
            "assigned_by": str(self._assigned_by) if self._assigned_by else None,
        }
