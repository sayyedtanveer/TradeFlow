"""Warehouse query handlers (read-only operations)."""

from typing import Any, Dict, List

from backend.app.domain.warehouse.repositories.warehouse_repository import (
    WarehouseRepository,
)
from backend.app.domain.warehouse.repositories.warehouse_user_assignment_repository import (
    WarehouseUserAssignmentRepository,
)
from backend.app.application.warehouse.queries import (
    GetWarehouseQuery,
    ListWarehousesQuery,
    GetWarehouseInventoryQuery,
    GetWarehouseOrdersQuery,
)


class GetWarehouseQueryHandler:
    """Handler for fetching warehouse details by ID."""

    def __init__(self, warehouse_repo: WarehouseRepository):
        self.warehouse_repo = warehouse_repo

    async def handle(self, query: GetWarehouseQuery) -> Dict[str, Any]:
        """
        Get warehouse details.

        Args:
            query: Query with tenant_id and warehouse_id

        Returns:
            Warehouse data as dictionary

        Raises:
            ValueError: If warehouse not found
        """
        warehouse = await self.warehouse_repo.get_by_id(
            id=query.warehouse_id,
            tenant_id=query.tenant_id,
        )
        if not warehouse:
            raise ValueError(f"Warehouse {query.warehouse_id} not found")
        return warehouse.to_dict()


class ListWarehousesQueryHandler:
    """Handler for listing warehouses with pagination."""

    def __init__(self, warehouse_repo: WarehouseRepository):
        self.warehouse_repo = warehouse_repo

    async def handle(self, query: ListWarehousesQuery) -> Dict[str, Any]:
        """
        List warehouses with pagination and optional active filter.

        Args:
            query: Query with pagination params and optional is_active filter

        Returns:
            Dictionary with items list, total count, and pagination info
        """
        warehouses = await self.warehouse_repo.list(
            tenant_id=query.tenant_id,
            is_active=query.is_active,
            page=query.page,
            page_size=query.page_size,
        )
        total = await self.warehouse_repo.count(
            tenant_id=query.tenant_id,
            is_active=query.is_active,
        )
        return {
            "items": [w.to_dict() for w in warehouses],
            "total": total,
            "page": query.page,
            "page_size": query.page_size,
        }


class GetWarehouseInventoryQueryHandler:
    """Handler for fetching inventory for a specific warehouse."""

    def __init__(
        self,
        warehouse_repo: WarehouseRepository,
    ):
        self.warehouse_repo = warehouse_repo

    async def handle(self, query: GetWarehouseInventoryQuery) -> Dict[str, Any]:
        """
        Get inventory for a warehouse.

        Validates the warehouse exists, then returns inventory data
        scoped to the warehouse. The actual inventory data retrieval
        is delegated to the inventory infrastructure layer.

        Args:
            query: Query with warehouse_id and pagination

        Returns:
            Dictionary with inventory items and pagination info

        Raises:
            ValueError: If warehouse not found
        """
        # Validate warehouse exists
        warehouse = await self.warehouse_repo.get_by_id(
            id=query.warehouse_id,
            tenant_id=query.tenant_id,
        )
        if not warehouse:
            raise ValueError(f"Warehouse {query.warehouse_id} not found")

        # Inventory data will be populated via the infrastructure layer
        # once warehouse-scoped inventory is implemented (task 2.6).
        # For now, return a structured response that the API layer can use.
        return {
            "warehouse_id": str(query.warehouse_id),
            "warehouse_name": warehouse.name,
            "items": [],
            "total": 0,
            "page": query.page,
            "page_size": query.page_size,
        }


class GetWarehouseOrdersQueryHandler:
    """Handler for fetching orders assigned to a specific warehouse."""

    def __init__(
        self,
        warehouse_repo: WarehouseRepository,
    ):
        self.warehouse_repo = warehouse_repo

    async def handle(self, query: GetWarehouseOrdersQuery) -> Dict[str, Any]:
        """
        Get orders assigned to a warehouse.

        Validates the warehouse exists, then returns orders assigned
        to it. The actual order data retrieval is delegated to the
        sales infrastructure layer.

        Args:
            query: Query with warehouse_id, optional status filter, and pagination

        Returns:
            Dictionary with order items and pagination info

        Raises:
            ValueError: If warehouse not found
        """
        # Validate warehouse exists
        warehouse = await self.warehouse_repo.get_by_id(
            id=query.warehouse_id,
            tenant_id=query.tenant_id,
        )
        if not warehouse:
            raise ValueError(f"Warehouse {query.warehouse_id} not found")

        # Order data will be populated via the sales infrastructure layer
        # once warehouse-scoped orders are implemented (task 4.x).
        # For now, return a structured response.
        return {
            "warehouse_id": str(query.warehouse_id),
            "warehouse_name": warehouse.name,
            "items": [],
            "total": 0,
            "page": query.page,
            "page_size": query.page_size,
        }
