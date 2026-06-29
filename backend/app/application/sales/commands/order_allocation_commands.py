"""Sales Order Allocation Commands."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
import uuid


@dataclass(frozen=True)
class OrderLineItemData:
    """Line item data for order allocation."""
    product_id: uuid.UUID
    quantity: int


@dataclass(frozen=True)
class AllocateOrderCommand:
    """Command to allocate an order to a warehouse."""
    tenant_id: uuid.UUID
    order_id: uuid.UUID
    line_items: List[OrderLineItemData] = field(default_factory=list)
    exclude_warehouse_ids: List[uuid.UUID] = field(default_factory=list)


@dataclass(frozen=True)
class AssignOrderToWarehouseCommand:
    """Command to explicitly assign an order to a specific warehouse."""
    tenant_id: uuid.UUID
    order_id: uuid.UUID
    warehouse_id: uuid.UUID
    assigned_by: uuid.UUID


@dataclass(frozen=True)
class ReassignOrderToWarehouseCommand:
    """Command to reassign an order to a different warehouse (when first allocation fails)."""
    tenant_id: uuid.UUID
    order_id: uuid.UUID
    new_warehouse_id: uuid.UUID
    reason: str
    reassigned_by: uuid.UUID


@dataclass(frozen=True)
class ReleaseOrderFromWarehouseCommand:
    """Command to release an order from warehouse (undo allocation)."""
    tenant_id: uuid.UUID
    order_id: uuid.UUID
    reason: Optional[str] = None
