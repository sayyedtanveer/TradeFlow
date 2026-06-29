"""Stock Aggregation API routes.

Provides endpoints for:
  - Check product availability across warehouses (client portal)
  - View warehouse inventory (admin)
  - Get coverage analysis (admin planning)
  - Find suitable warehouses for order (used by allocation service)
"""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.application.inventory.services.stock_aggregation_service import (
    StockAggregationService,
)
from backend.app.infrastructure.persistence.repositories.warehouse_product_assignment_repository import (
    SqlAlchemyWarehouseProductAssignmentRepository,
)
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_tenant_id,
)
from backend.app.interfaces.api.v1.schemas.stock_aggregation_schemas import (
    ProductAvailabilityResponse,
    WarehouseStockListResponse,
    CoverageAnalysisResponse,
    WarehouseStockResponse,
)

router = APIRouter(
    prefix="/inventory",
    tags=["Stock Aggregation"],
)


# ── Public (Client Portal) - Product Availability ─────────────────────────────

@router.get(
    "/products/{product_id}/availability",
    response_model=ProductAvailabilityResponse,
    summary="Check product availability",
    description="See which warehouses have this product in stock (client view).",
)
async def check_product_availability(
    product_id: uuid.UUID,
    include_unavailable: bool = Query(
        False,
        description="Include warehouses where product is marked unavailable",
    ),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    container = Depends(get_container),
) -> ProductAvailabilityResponse:
    """Get availability of a product across warehouses."""
    try:
        async with container.uow() as uow:
            warehouse_product_repo = SqlAlchemyWarehouseProductAssignmentRepository(uow)
            service = StockAggregationService(warehouse_product_repo, uow)

            availability = await service.get_product_availability(
            tenant_id=tenant_id,
            product_id=product_id,
        )

        # Filter unavailable if not requested
        warehouses = availability.warehouses
        if not include_unavailable:
            warehouses = [w for w in warehouses if w.is_available]

        return ProductAvailabilityResponse(
            product_id=str(product_id),
            is_available_anywhere=availability.is_available_anywhere,
            available_warehouse_count=len(warehouses),
            warehouses=[
                WarehouseStockResponse(
                    warehouse_id=str(w.warehouse_id),
                    is_available=w.is_available,
                    default_reorder_level=w.default_reorder_level,
                )
                for w in warehouses
            ],
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get product availability",
        )


# ── Admin - Warehouse Inventory ────────────────────────────────────────────────

@router.get(
    "/warehouses/{warehouse_id}/inventory",
    response_model=WarehouseStockListResponse,
    summary="Get warehouse inventory",
    description="View all products stocked at a specific warehouse.",
)
async def get_warehouse_inventory(
    warehouse_id: uuid.UUID,
    include_unavailable: bool = Query(
        False,
        description="Include products marked unavailable",
    ),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    container = Depends(get_container),
) -> WarehouseStockListResponse:
    """Get inventory for a warehouse."""
    try:
        async with container.uow() as uow:
            warehouse_product_repo = SqlAlchemyWarehouseProductAssignmentRepository(uow)
            service = StockAggregationService(warehouse_product_repo, uow)

            warehouse_info = await service.get_products_for_warehouse(
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
        )

        # Filter unavailable if not requested
        products = warehouse_info.products
        if not include_unavailable:
            products = [p for p in products if p.is_available]

        return WarehouseStockListResponse(
            warehouse_id=str(warehouse_id),
            product_count=len(products),
            products=[
                {
                    "product_id": str(p.product_id),
                    "is_available": p.is_available,
                    "default_reorder_level": p.default_reorder_level,
                }
                for p in products
            ],
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get warehouse inventory",
        )


# ── Admin - Warehouse Coverage for Products ────────────────────────────────────

@router.get(
    "/warehouses-for-products",
    response_model=List[str],
    summary="Find warehouses with all products",
    description="Find which warehouses stock ALL products in a list (for order fulfillment).",
)
async def find_warehouses_with_products(
    product_ids: List[uuid.UUID] = Query(
        ...,
        description="Product IDs to check",
        min_items=1,
    ),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    container = Depends(get_container),
) -> List[str]:
    """Find warehouses that can fulfill a set of products."""
    try:
        async with container.uow() as uow:
            warehouse_product_repo = SqlAlchemyWarehouseProductAssignmentRepository(uow)
            service = StockAggregationService(warehouse_product_repo, uow)

            warehouse_ids = await service.get_warehouses_with_all_products(
            tenant_id=tenant_id,
            product_ids=product_ids,
        )

        return [str(wh_id) for wh_id in warehouse_ids]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find warehouses",
        )


# ── Admin - Coverage Analysis ──────────────────────────────────────────────────

@router.get(
    "/coverage-analysis",
    response_model=CoverageAnalysisResponse,
    summary="Get product-warehouse coverage analysis",
    description="Analyze how products are distributed across warehouses.",
)
async def get_coverage_analysis(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    container = Depends(get_container),
) -> CoverageAnalysisResponse:
    """Get coverage analysis of product distribution."""
    try:
        async with container.uow() as uow:
            warehouse_product_repo = SqlAlchemyWarehouseProductAssignmentRepository(uow)
            service = StockAggregationService(warehouse_product_repo, uow)

            analysis = await service.get_coverage_analysis(
            tenant_id=tenant_id,
        )

        coverage_pct = (
            (analysis.total_products - analysis.products_unavailable)
            / analysis.total_products
            * 100
            if analysis.total_products > 0
            else 0
        )

        return CoverageAnalysisResponse(
            total_products=analysis.total_products,
            products_in_all_warehouses=analysis.products_in_all_warehouses,
            products_in_single_warehouse=analysis.products_in_single_warehouse,
            products_unavailable=analysis.products_unavailable,
            average_warehouses_per_product=analysis.average_warehouses_per_product,
            coverage_percentage=coverage_pct,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get coverage analysis",
        )
