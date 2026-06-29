"""Warehouse-Product Assignment Repository Interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import List, Optional

from backend.app.domain.warehouse.entities.warehouse_product_assignment import (
    WarehouseProductAssignment,
)


class WarehouseProductAssignmentRepository(ABC):
    """
    Abstract repository interface for Warehouse-Product Assignment entities.

    Implementations must filter by tenant_id and respect soft-delete.
    """

    @abstractmethod
    async def get_by_id(
        self, id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[WarehouseProductAssignment]:
        """Return assignment by ID or None (excludes soft-deleted)."""
        ...

    @abstractmethod
    async def get_by_warehouse_and_product(
        self,
        warehouse_id: uuid.UUID,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Optional[WarehouseProductAssignment]:
        """Return assignment for specific warehouse-product combo."""
        ...

    @abstractmethod
    async def get_warehouses_for_product(
        self, product_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> List[WarehouseProductAssignment]:
        """Return all warehouses that carry this product (only available=True)."""
        ...

    @abstractmethod
    async def get_products_for_warehouse(
        self, warehouse_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> List[WarehouseProductAssignment]:
        """Return all products assigned to this warehouse (only available=True)."""
        ...

    @abstractmethod
    async def get_all_for_warehouse(
        self, warehouse_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> List[WarehouseProductAssignment]:
        """Return all assignments for warehouse, including unavailable."""
        ...

    @abstractmethod
    async def save(self, entity: WarehouseProductAssignment) -> WarehouseProductAssignment:
        """Insert or update the assignment."""
        ...

    @abstractmethod
    async def delete(self, id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        """Soft-delete the assignment."""
        ...
