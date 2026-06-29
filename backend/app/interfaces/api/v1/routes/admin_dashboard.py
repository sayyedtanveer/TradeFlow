"""Admin Dashboard API routes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.application.admin.services.admin_dashboard_service import (
    AdminDashboardService,
)
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_tenant_id,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.interfaces.api.v1.schemas.admin_dashboard_schemas import (
    AdminDashboardResponse,
    OrderMetricsResponse,
    InventoryMetricsResponse,
    SystemHealthResponse,
    WarehouseMetricResponse,
)

router = APIRouter(
    prefix="/admin/dashboard",
    tags=["Admin Dashboard"],
)


@router.get(
    "",
    response_model=AdminDashboardResponse,
    summary="Get admin dashboard",
    description="Get operational metrics and dashboard for admin users.",
)
async def get_admin_dashboard(
    period: str = Query(
        "last_7_days",
        description="Time period: last_7_days, last_30_days, last_90_days",
    ),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    container = Depends(get_container),
    _: None = Depends(require_permission("admin:view_dashboard")),
) -> AdminDashboardResponse:
    """Get admin dashboard with operational metrics."""
    try:
        async with container.uow() as uow:
            dashboard_service = AdminDashboardService(uow)

            # Get metrics
            days = _parse_period(period)
            order_metrics = await dashboard_service.get_order_metrics(tenant_id, days)
            inventory_metrics = await dashboard_service.get_inventory_metrics(tenant_id)
            system_health = await dashboard_service.get_system_health(tenant_id)
            warehouse_metrics = await dashboard_service.get_warehouse_metrics(tenant_id)

            # Calculate derived metrics
            allocation_rate = (
                (order_metrics.total_allocated / order_metrics.total_pending * 100)
                if order_metrics.total_pending > 0
                else 0
            )

        stockout_risk = (
            (inventory_metrics.out_of_stock_products + inventory_metrics.low_stock_products)
            / inventory_metrics.total_products
            * 100
            if inventory_metrics.total_products > 0
            else 0
        )

        # Generate alerts
        alerts = _generate_alerts(
            order_metrics, inventory_metrics, system_health
        )

        return AdminDashboardResponse(
            timestamp=datetime.now(timezone.utc),
            period=period,
            order_metrics=OrderMetricsResponse(
                total_pending=order_metrics.total_pending,
                total_allocated=order_metrics.total_allocated,
                total_fulfilled=order_metrics.total_fulfilled,
                unallocated_count=order_metrics.unallocated_count,
                average_allocation_time=order_metrics.average_allocation_time,
                allocation_rate=allocation_rate,
            ),
            inventory_metrics=InventoryMetricsResponse(
                total_products=inventory_metrics.total_products,
                low_stock_products=inventory_metrics.low_stock_products,
                out_of_stock_products=inventory_metrics.out_of_stock_products,
                overstock_products=inventory_metrics.overstock_products,
                stockout_risk=stockout_risk,
            ),
            system_health=SystemHealthResponse(
                allocation_success_rate=system_health.allocation_success_rate,
                order_fulfillment_rate=system_health.order_fulfillment_rate,
                inventory_accuracy=system_health.inventory_accuracy,
                warehouse_utilization=system_health.warehouse_utilization,
                health_status=_get_health_status(system_health),
            ),
            warehouses=[
                WarehouseMetricResponse(
                    warehouse_id=str(w.warehouse_id),
                    warehouse_name=w.warehouse_name,
                    total_products=w.total_products,
                    orders_pending=w.orders_pending,
                    orders_allocated=w.orders_allocated,
                    orders_fulfilled=w.orders_fulfilled,
                    utilization_percentage=0.0,  # Would be calculated from actual data
                )
                for w in warehouse_metrics
            ],
            alerts=alerts,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dashboard metrics",
        )


@router.get(
    "/order-metrics",
    response_model=OrderMetricsResponse,
    summary="Get order metrics only",
    description="Get order-specific metrics.",
)
async def get_order_metrics(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    container = Depends(get_container),
    _: None = Depends(require_permission("admin:view_dashboard")),
) -> OrderMetricsResponse:
    """Get order metrics."""
    try:
        async with container.uow() as uow:
            dashboard_service = AdminDashboardService(uow)

            metrics = await dashboard_service.get_order_metrics(tenant_id)

        allocation_rate = (
            (metrics.total_allocated / metrics.total_pending * 100)
            if metrics.total_pending > 0
            else 0
        )

        return OrderMetricsResponse(
            total_pending=metrics.total_pending,
            total_allocated=metrics.total_allocated,
            total_fulfilled=metrics.total_fulfilled,
            unallocated_count=metrics.unallocated_count,
            average_allocation_time=metrics.average_allocation_time,
            allocation_rate=allocation_rate,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get order metrics",
        )


@router.get(
    "/inventory-metrics",
    response_model=InventoryMetricsResponse,
    summary="Get inventory metrics only",
    description="Get inventory-specific metrics.",
)
async def get_inventory_metrics(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    container = Depends(get_container),
    _: None = Depends(require_permission("admin:view_dashboard")),
) -> InventoryMetricsResponse:
    """Get inventory metrics."""
    try:
        async with container.uow() as uow:
            dashboard_service = AdminDashboardService(uow)

            metrics = await dashboard_service.get_inventory_metrics(tenant_id)

        stockout_risk = (
            (metrics.out_of_stock_products + metrics.low_stock_products)
            / metrics.total_products
            * 100
            if metrics.total_products > 0
            else 0
        )

        return InventoryMetricsResponse(
            total_products=metrics.total_products,
            low_stock_products=metrics.low_stock_products,
            out_of_stock_products=metrics.out_of_stock_products,
            overstock_products=metrics.overstock_products,
            stockout_risk=stockout_risk,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get inventory metrics",
        )


@router.get(
    "/system-health",
    response_model=SystemHealthResponse,
    summary="Get system health",
    description="Get overall system health indicators.",
)
async def get_system_health(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    container = Depends(get_container),
    _: None = Depends(require_permission("admin:view_dashboard")),
) -> SystemHealthResponse:
    """Get system health."""
    try:
        async with container.uow() as uow:
            dashboard_service = AdminDashboardService(uow)

            health = await dashboard_service.get_system_health(tenant_id)

        return SystemHealthResponse(
            allocation_success_rate=health.allocation_success_rate,
            order_fulfillment_rate=health.order_fulfillment_rate,
            inventory_accuracy=health.inventory_accuracy,
            warehouse_utilization=health.warehouse_utilization,
            health_status=_get_health_status(health),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system health",
        )


# ── Helper Functions ──────────────────────────────────────────────────────────

def _parse_period(period: str) -> int:
    """Parse period string to number of days."""
    periods = {
        "last_7_days": 7,
        "last_30_days": 30,
        "last_90_days": 90,
    }
    return periods.get(period, 7)


def _get_health_status(health) -> str:
    """Determine overall health status."""
    avg_health = (
        health.allocation_success_rate
        + health.order_fulfillment_rate
        + health.inventory_accuracy
        + health.warehouse_utilization
    ) / 4

    if avg_health >= 90:
        return "HEALTHY"
    elif avg_health >= 70:
        return "DEGRADED"
    else:
        return "CRITICAL"


def _generate_alerts(order_metrics, inventory_metrics, system_health) -> List[str]:
    """Generate alerts for admin attention."""
    alerts = []

    if order_metrics.unallocated_count > 0:
        alerts.append(
            f"⚠️ {order_metrics.unallocated_count} orders pending allocation"
        )

    if inventory_metrics.out_of_stock_products > 0:
        alerts.append(
            f"🚨 {inventory_metrics.out_of_stock_products} products out of stock"
        )

    if inventory_metrics.low_stock_products > 5:
        alerts.append(
            f"⚠️ {inventory_metrics.low_stock_products} products below reorder level"
        )

    if system_health.allocation_success_rate < 70:
        alerts.append("🔴 Order allocation success rate below 70%")

    if system_health.order_fulfillment_rate < 80:
        alerts.append("🔴 Order fulfillment rate below 80%")

    return alerts
