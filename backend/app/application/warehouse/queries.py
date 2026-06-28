"""Warehouse application queries (CQRS pattern)."""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class GetWarehouseQuery:
    """Get warehouse details by ID."""

    tenant_id: UUID
    warehouse_id: UUID


@dataclass(frozen=True)
class ListWarehousesQuery:
    """List warehouses with pagination and optional status filter."""

    tenant_id: UUID
    is_active: Optional[bool] = None
    page: int = 1
    page_size: int = 20


@dataclass(frozen=True)
class GetWarehouseInventoryQuery:
    """Get inventory for a specific warehouse."""

    tenant_id: UUID
    warehouse_id: UUID
    page: int = 1
    page_size: int = 50


@dataclass(frozen=True)
class GetWarehouseOrdersQuery:
    """Get orders assigned to a specific warehouse."""

    tenant_id: UUID
    warehouse_id: UUID
    status: Optional[str] = None
    page: int = 1
    page_size: int = 20
