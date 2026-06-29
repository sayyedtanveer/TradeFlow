"""Admin Dashboard Service - Aggregates operational metrics."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork


class AdminDashboardService:
    """Service for operational dashboard aggregations."""

    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self._uow = uow

    async def get_order_metrics(
        self,
        tenant_id: uuid.UUID,
        days: int = 7,
    ) -> OrderMetrics:
        """Get order metrics for dashboard (pending, allocated, etc)."""
        # This would be implemented with actual queries
        # Placeholder for now
        return OrderMetrics(
            total_pending=0,
            total_allocated=0,
            total_fulfilled=0,
            unallocated_count=0,
            average_allocation_time=0,
        )

    async def get_warehouse_metrics(
        self,
        tenant_id: uuid.UUID,
    ) -> List[WarehouseMetric]:
        """Get metrics for each warehouse."""
        # Placeholder
        return []

    async def get_inventory_metrics(
        self,
        tenant_id: uuid.UUID,
    ) -> InventoryMetrics:
        """Get inventory metrics (low stock, overstock, etc)."""
        # Placeholder
        return InventoryMetrics(
            total_products=0,
            low_stock_products=0,
            out_of_stock_products=0,
            overstock_products=0,
        )

    async def get_system_health(
        self,
        tenant_id: uuid.UUID,
    ) -> SystemHealth:
        """Get overall system health indicators."""
        # Placeholder
        return SystemHealth(
            allocation_success_rate=0.0,
            order_fulfillment_rate=0.0,
            inventory_accuracy=0.0,
            warehouse_utilization=0.0,
        )


# ── DTOs ──────────────────────────────────────────────────────────────────────

class OrderMetrics:
    """Order-related metrics."""

    def __init__(
        self,
        total_pending: int,
        total_allocated: int,
        total_fulfilled: int,
        unallocated_count: int,
        average_allocation_time: float,
    ):
        self.total_pending = total_pending
        self.total_allocated = total_allocated
        self.total_fulfilled = total_fulfilled
        self.unallocated_count = unallocated_count
        self.average_allocation_time = average_allocation_time


class WarehouseMetric:
    """Metrics for a single warehouse."""

    def __init__(
        self,
        warehouse_id: uuid.UUID,
        warehouse_name: str,
        total_products: int,
        orders_pending: int,
        orders_allocated: int,
        orders_fulfilled: int,
    ):
        self.warehouse_id = warehouse_id
        self.warehouse_name = warehouse_name
        self.total_products = total_products
        self.orders_pending = orders_pending
        self.orders_allocated = orders_allocated
        self.orders_fulfilled = orders_fulfilled


class InventoryMetrics:
    """Inventory-related metrics."""

    def __init__(
        self,
        total_products: int,
        low_stock_products: int,
        out_of_stock_products: int,
        overstock_products: int,
    ):
        self.total_products = total_products
        self.low_stock_products = low_stock_products
        self.out_of_stock_products = out_of_stock_products
        self.overstock_products = overstock_products


class SystemHealth:
    """System health indicators."""

    def __init__(
        self,
        allocation_success_rate: float,
        order_fulfillment_rate: float,
        inventory_accuracy: float,
        warehouse_utilization: float,
    ):
        self.allocation_success_rate = allocation_success_rate
        self.order_fulfillment_rate = order_fulfillment_rate
        self.inventory_accuracy = inventory_accuracy
        self.warehouse_utilization = warehouse_utilization
