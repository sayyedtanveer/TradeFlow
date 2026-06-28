"""Warehouse User Assignment Repository Interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import List, Optional

from backend.app.domain.warehouse.entities.warehouse_user_assignment import (
    WarehouseUserAssignment,
)


class WarehouseUserAssignmentRepository(ABC):
    """
    Abstract repository interface for WarehouseUserAssignment entities.

    Enforces the single-warehouse-per-user invariant at the persistence level.
    """

    @abstractmethod
    async def get_by_id(
        self, id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[WarehouseUserAssignment]:
        """Return assignment by ID or None."""
        ...

    @abstractmethod
    async def get_by_user_id(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[WarehouseUserAssignment]:
        """
        Return the current active assignment for a user.

        A user can only have one active assignment at a time.
        """
        ...

    @abstractmethod
    async def find_by_warehouse(
        self, tenant_id: uuid.UUID, warehouse_id: uuid.UUID
    ) -> List[WarehouseUserAssignment]:
        """Return all user assignments for a given warehouse."""
        ...

    @abstractmethod
    async def save(self, entity: WarehouseUserAssignment) -> WarehouseUserAssignment:
        """Insert or update the assignment."""
        ...

    @abstractmethod
    async def delete(self, id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        """Remove (soft-delete) the assignment."""
        ...

    @abstractmethod
    async def delete_by_user_id(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """Remove all assignments for a user (used during reassignment)."""
        ...
