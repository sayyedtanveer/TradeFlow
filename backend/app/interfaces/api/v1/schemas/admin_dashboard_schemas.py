"""API Schemas for Admin Dashboard."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime


# ── Response Schemas ──────────────────────────────────────────────────────────

class OrderMetricsResponse(BaseModel):
    """Order metrics for dashboard."""
    total_pending: int = Field(description="Total pending orders")
    total_allocated: int = Field(description="Orders allocated to warehouse")
    total_fulfilled: int = Field(description="Orders fulfilled/completed")
    unallocated_count: int = Field(description="Orders not yet allocated")
    average_allocation_time: float = Field(
        description="Average time to allocate order (minutes)"
    )
    allocation_rate: float = Field(
        description="Percentage of orders allocated",
    )


class WarehouseMetricResponse(BaseModel):
    """Metrics for a warehouse."""
    warehouse_id: str
    warehouse_name: str
    total_products: int = Field(description="Products in this warehouse")
    orders_pending: int
    orders_allocated: int
    orders_fulfilled: int
    utilization_percentage: float = Field(
        description="Percentage of warehouse capacity used",
    )


class InventoryMetricsResponse(BaseModel):
    """Inventory metrics for dashboard."""
    total_products: int
    low_stock_products: int = Field(
        description="Products near reorder level",
    )
    out_of_stock_products: int = Field(
        description="Products with zero stock everywhere",
    )
    overstock_products: int = Field(
        description="Products over safe stock level",
    )
    stockout_risk: float = Field(
        description="Percentage of products at risk of stockout",
    )


class SystemHealthResponse(BaseModel):
    """System health indicators."""
    allocation_success_rate: float = Field(
        ge=0,
        le=100,
        description="Percentage of orders successfully allocated",
    )
    order_fulfillment_rate: float = Field(
        ge=0,
        le=100,
        description="Percentage of orders fulfilled on time",
    )
    inventory_accuracy: float = Field(
        ge=0,
        le=100,
        description="Percentage of inventory records accurate vs physical count",
    )
    warehouse_utilization: float = Field(
        ge=0,
        le=100,
        description="Average warehouse capacity utilization",
    )
    health_status: str = Field(
        description="Overall health: HEALTHY, DEGRADED, CRITICAL",
    )


class AdminDashboardResponse(BaseModel):
    """Complete admin dashboard."""
    timestamp: datetime
    period: str = Field(description="e.g., 'last_7_days'")
    
    # High-level metrics
    order_metrics: OrderMetricsResponse
    inventory_metrics: InventoryMetricsResponse
    system_health: SystemHealthResponse
    
    # Warehouse-level breakdown
    warehouses: List[WarehouseMetricResponse] = Field(default_factory=list)
    
    # Alerts/notifications
    alerts: List[str] = Field(
        default_factory=list,
        description="Critical alerts for admin attention",
    )
