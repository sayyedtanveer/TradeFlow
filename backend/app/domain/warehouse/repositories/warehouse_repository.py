"""Warehouse Repository Interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import List, Optional

from backend.app.domain.warehouse.entities.warehouse import Warehouse


class WarehouseRepository(ABC):
    """
    Abstract repository interface for Warehouse aggregate root.

    Implementations must filter by tenant_id and respect soft-delete.
    """

    @abstractmethod
    async def get_by_id(
        self, id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[Warehouse]:
        """Return warehouse by ID or None (excludes soft-deleted)."""
        ...

    @abstractmethod
    async def get_by_name(
        self, tenant_id: uuid.UUID, name: str
    ) -> Optional[Warehouse]:
        """Return warehouse by name within a tenant (for uniqueness checks)."""
        ...

    @abstractmethod
    async def save(self, entity: Warehouse) -> Warehouse:
        """Insert or update the warehouse."""
        ...

    @abstractmethod
    async def delete(self, id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        """Soft-delete the warehouse."""
        ...

    @abstractmethod
    async def list(
        self,
        tenant_id: uuid.UUID,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[Warehouse]:
        """Return paginated list of warehouses (excludes soft-deleted)."""
        ...

    @abstractmethod
    async def count(
        self,
        tenant_id: uuid.UUID,
        is_active: Optional[bool] = None,
    ) -> int:
        """Return total count of warehouses matching filters."""
        ...
