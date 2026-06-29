"""Warehouse command handlers package.

This package exposes the warehouse command handlers from the parent
warehouse_command_handlers module, avoiding the file/package import
collision between the command_handlers module and package.
"""

from backend.app.application.warehouse.warehouse_command_handlers import (
    AcceptOrderCommandHandler,
    AssignUserToWarehouseCommandHandler,
    CreateWarehouseCommandHandler,
    DeactivateWarehouseCommandHandler,
    RemoveUserFromWarehouseCommandHandler,
    UpdateWarehouseCommandHandler,
)

__all__ = [
    "AcceptOrderCommandHandler",
    "AssignUserToWarehouseCommandHandler",
    "CreateWarehouseCommandHandler",
    "DeactivateWarehouseCommandHandler",
    "RemoveUserFromWarehouseCommandHandler",
    "UpdateWarehouseCommandHandler",
]
