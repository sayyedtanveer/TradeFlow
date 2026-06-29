"""Warehouse-Product Assignment Commands."""

from __future__ import annotations

from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class AssignProductToWarehouseCommand:
    """Command to assign a product to a warehouse (make it available)."""
    tenant_id: uuid.UUID
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    default_reorder_level: int = 0


@dataclass(frozen=True)
class UnassignProductFromWarehouseCommand:
    """Command to remove a product from a warehouse."""
    tenant_id: uuid.UUID
    warehouse_id: uuid.UUID
    product_id: uuid.UUID


@dataclass(frozen=True)
class MarkProductUnavailableCommand:
    """Command to mark a product as unavailable in a warehouse (soft disable)."""
    tenant_id: uuid.UUID
    warehouse_id: uuid.UUID
    product_id: uuid.UUID


@dataclass(frozen=True)
class MarkProductAvailableCommand:
    """Command to mark a product as available in a warehouse (re-enable)."""
    tenant_id: uuid.UUID
    warehouse_id: uuid.UUID
    product_id: uuid.UUID


@dataclass(frozen=True)
class UpdateReorderLevelCommand:
    """Command to update default reorder level for warehouse-product combo."""
    tenant_id: uuid.UUID
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    default_reorder_level: int
