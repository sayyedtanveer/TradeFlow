"""Warehouse domain module.

Contains all domain logic for warehouse management:
- Entities: Warehouse, WarehouseUserAssignment, WarehouseProductThreshold
- Value Objects: Address
- Repositories: WarehouseRepository, WarehouseUserAssignmentRepository
"""

from backend.app.domain.warehouse.entities import (
    Warehouse,
    WarehouseUserAssignment,
    WarehouseProductThreshold,
)

from backend.app.domain.warehouse.value_objects import Address

from backend.app.domain.warehouse.repositories import (
    WarehouseRepository,
    WarehouseUserAssignmentRepository,
)

__all__ = [
    # Entities
    "Warehouse",
    "WarehouseUserAssignment",
    "WarehouseProductThreshold",
    # Value Objects
    "Address",
    # Repositories
    "WarehouseRepository",
    "WarehouseUserAssignmentRepository",
]
