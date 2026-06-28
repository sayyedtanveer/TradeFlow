"""Warehouse application layer.

Contains CQRS commands and queries for warehouse management:
- Commands: CreateWarehouse, UpdateWarehouse, DeactivateWarehouse, AssignUserToWarehouse, RemoveUserFromWarehouse
- Queries: GetWarehouse, ListWarehouses, GetWarehouseInventory, GetWarehouseOrders
"""

from backend.app.application.warehouse.commands import (
    CreateWarehouseCommand,
    UpdateWarehouseCommand,
    DeactivateWarehouseCommand,
    AssignUserToWarehouseCommand,
    RemoveUserFromWarehouseCommand,
)
from backend.app.application.warehouse.queries import (
    GetWarehouseQuery,
    ListWarehousesQuery,
    GetWarehouseInventoryQuery,
    GetWarehouseOrdersQuery,
)

__all__ = [
    # Commands
    "CreateWarehouseCommand",
    "UpdateWarehouseCommand",
    "DeactivateWarehouseCommand",
    "AssignUserToWarehouseCommand",
    "RemoveUserFromWarehouseCommand",
    # Queries
    "GetWarehouseQuery",
    "ListWarehousesQuery",
    "GetWarehouseInventoryQuery",
    "GetWarehouseOrdersQuery",
]
