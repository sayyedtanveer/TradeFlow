"""Warehouse domain repository interfaces."""

from backend.app.domain.warehouse.repositories.warehouse_repository import WarehouseRepository
from backend.app.domain.warehouse.repositories.warehouse_user_assignment_repository import (
    WarehouseUserAssignmentRepository,
)

__all__ = [
    "WarehouseRepository",
    "WarehouseUserAssignmentRepository",
]
