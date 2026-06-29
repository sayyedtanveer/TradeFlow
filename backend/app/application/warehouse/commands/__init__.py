"""Warehouse application commands (CQRS pattern).

This package exposes command dataclasses for warehouse operations.
Moved here to avoid module/package name collision with a top-level
`commands.py` file in the same directory.
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class CreateWarehouseCommand:
    """Create a new warehouse."""

    tenant_id: UUID
    name: str
    address_street: str
    address_city: str
    address_region: str
    address_postal_code: str
    address_country: str
    phone: str
    created_by: UUID
    email: Optional[str] = None


@dataclass(frozen=True)
class UpdateWarehouseCommand:
    """Update an existing warehouse profile."""

    tenant_id: UUID
    warehouse_id: UUID
    updated_by: UUID
    name: Optional[str] = None
    address_street: Optional[str] = None
    address_city: Optional[str] = None
    address_region: Optional[str] = None
    address_postal_code: Optional[str] = None
    address_country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


@dataclass(frozen=True)
class DeactivateWarehouseCommand:
    """Deactivate a warehouse (prevents new order assignments)."""

    tenant_id: UUID
    warehouse_id: UUID
    deactivated_by: UUID


@dataclass(frozen=True)
class AssignUserToWarehouseCommand:
    """
    Assign a user to a warehouse.

    If the user is already assigned to another warehouse, the previous
    assignment is revoked (single-warehouse-per-user invariant).
    """

    tenant_id: UUID
    warehouse_id: UUID
    user_id: UUID
    assigned_by: UUID


@dataclass(frozen=True)
class RemoveUserFromWarehouseCommand:
    """Remove a user's warehouse assignment."""

    tenant_id: UUID
    warehouse_id: UUID
    user_id: UUID
    removed_by: UUID


@dataclass(frozen=True)
class AcceptOrderCommand:
    """
    Warehouse user accepts an order assigned to their warehouse.

    Transitions the order from ASSIGNED → ACCEPTED and generates
    a pick list containing product details and storage locations.

    Requirements: 7.2, 7.3
    """

    tenant_id: UUID
    order_id: UUID
    warehouse_id: UUID
    accepted_by: UUID


__all__ = [
    "CreateWarehouseCommand",
    "UpdateWarehouseCommand",
    "DeactivateWarehouseCommand",
    "AssignUserToWarehouseCommand",
    "RemoveUserFromWarehouseCommand",
    "AcceptOrderCommand",
]
