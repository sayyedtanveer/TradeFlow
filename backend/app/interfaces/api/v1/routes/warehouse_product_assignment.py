"""Warehouse-Product Assignment API routes."""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.app.application.warehouse.command_handlers.warehouse_product_assignment_handlers import (
    AssignProductToWarehouseCommandHandler,
    UnassignProductFromWarehouseCommandHandler,
    MarkProductUnavailableCommandHandler,
    MarkProductAvailableCommandHandler,
    UpdateReorderLevelCommandHandler,
)
from backend.app.application.warehouse.commands.warehouse_product_assignment_commands import (
    AssignProductToWarehouseCommand,
    UnassignProductFromWarehouseCommand,
    MarkProductUnavailableCommand,
    MarkProductAvailableCommand,
    UpdateReorderLevelCommand,
)
from backend.app.infrastructure.persistence.repositories.warehouse_product_assignment_repository import (
    SqlAlchemyWarehouseProductAssignmentRepository,
)
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_tenant_id,
    get_current_user_id,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.interfaces.api.v1.schemas.warehouse_product_assignment_schemas import (
    AssignProductRequest,
    WarehouseProductAssignmentListResponse,
    WarehouseProductAssignmentResponse,
    UpdateReorderLevelRequest,
    AvailableWarehouseResponse,
    ProductAvailabilityResponse,
)

router = APIRouter(
    prefix="/warehouses",
    tags=["Warehouse-Product Assignments"],
)


async def _error_status(message: str) -> int:
    """Map domain error messages to HTTP status codes."""
    normalized = message.lower()
    if "not found" in normalized:
        return status.HTTP_404_NOT_FOUND
    if "not assigned" in normalized:
        return status.HTTP_404_NOT_FOUND
    if "already exists" in normalized:
        return status.HTTP_409_CONFLICT
    return status.HTTP_400_BAD_REQUEST


# ── Assign/Unassign Products ──────────────────────────────────────────────────

@router.post(
    "/{warehouse_id}/products",
    response_model=WarehouseProductAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign product to warehouse",
    description="Assign a product to a warehouse, making it available for inventory operations.",
)
async def assign_product_to_warehouse(
    warehouse_id: uuid.UUID,
    request: AssignProductRequest,
    req: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    container = Depends(get_container),
    _: None = Depends(require_permission("warehouse:manage")),
) -> WarehouseProductAssignmentResponse:
    """Assign a product to a warehouse."""
    try:
        async with container.uow() as uow:
            repo = SqlAlchemyWarehouseProductAssignmentRepository(uow)
            handler = AssignProductToWarehouseCommandHandler(repo, uow)

        cmd = AssignProductToWarehouseCommand(
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
            product_id=request.product_id,
            default_reorder_level=request.default_reorder_level,
        )

        result = await handler.handle(cmd)

        return WarehouseProductAssignmentResponse(
            id=result.id,
            warehouse_id=result.warehouse_id,
            product_id=result.product_id,
            is_available=result.is_available,
            default_reorder_level=result.default_reorder_level,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign product",
        )


@router.delete(
    "/{warehouse_id}/products/{product_id}",
    status_code=status.HTTP_200_OK,
    summary="Unassign product from warehouse",
    description="Remove a product from a warehouse (soft delete).",
)
async def unassign_product_from_warehouse(
    warehouse_id: uuid.UUID,
    product_id: uuid.UUID,
    req: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    container = Depends(get_container),
    _: None = Depends(require_permission("warehouse:manage")),
) -> None:
    """Remove a product from a warehouse."""
    try:
        async with container.uow() as uow:
            repo = SqlAlchemyWarehouseProductAssignmentRepository(uow)
            handler = UnassignProductFromWarehouseCommandHandler(repo, uow)

        cmd = UnassignProductFromWarehouseCommand(
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
        )

        await handler.handle(cmd)

        return {"message": "unassigned"}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unassign product",
        )


# ── Availability Management ───────────────────────────────────────────────────

@router.patch(
    "/{warehouse_id}/products/{product_id}/mark-unavailable",
    response_model=WarehouseProductAssignmentResponse,
    summary="Mark product unavailable",
    description="Temporarily mark a product as unavailable in a warehouse.",
)
async def mark_product_unavailable(
    warehouse_id: uuid.UUID,
    product_id: uuid.UUID,
    req: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    container = Depends(get_container),
    _: None = Depends(require_permission("warehouse:manage")),
) -> WarehouseProductAssignmentResponse:
    """Mark a product as unavailable in a warehouse."""
    try:
        async with container.uow() as uow:
            repo = SqlAlchemyWarehouseProductAssignmentRepository(uow)
            handler = MarkProductUnavailableCommandHandler(repo, uow)

        cmd = MarkProductUnavailableCommand(
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
        )

        result = await handler.handle(cmd)

        return WarehouseProductAssignmentResponse(
            id=result.id,
            warehouse_id=result.warehouse_id,
            product_id=result.product_id,
            is_available=result.is_available,
            default_reorder_level=result.default_reorder_level,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark product unavailable",
        )


@router.patch(
    "/{warehouse_id}/products/{product_id}/mark-available",
    response_model=WarehouseProductAssignmentResponse,
    summary="Mark product available",
    description="Mark a product as available in a warehouse.",
)
async def mark_product_available(
    warehouse_id: uuid.UUID,
    product_id: uuid.UUID,
    req: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    container = Depends(get_container),
    _: None = Depends(require_permission("warehouse:manage")),
) -> WarehouseProductAssignmentResponse:
    """Mark a product as available in a warehouse."""
    try:
        async with container.uow() as uow:
            repo = SqlAlchemyWarehouseProductAssignmentRepository(uow)
            handler = MarkProductAvailableCommandHandler(repo, uow)

        cmd = MarkProductAvailableCommand(
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
        )

        result = await handler.handle(cmd)

        return WarehouseProductAssignmentResponse(
            id=result.id,
            warehouse_id=result.warehouse_id,
            product_id=result.product_id,
            is_available=result.is_available,
            default_reorder_level=result.default_reorder_level,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark product available",
        )


# ── Reorder Level Management ──────────────────────────────────────────────────

@router.patch(
    "/{warehouse_id}/products/{product_id}/reorder-level",
    response_model=WarehouseProductAssignmentResponse,
    summary="Update product reorder level",
    description="Update the default reorder level for a warehouse-product combo.",
)
async def update_reorder_level(
    warehouse_id: uuid.UUID,
    product_id: uuid.UUID,
    request: UpdateReorderLevelRequest,
    req: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    container = Depends(get_container),
    _: None = Depends(require_permission("warehouse:manage")),
) -> WarehouseProductAssignmentResponse:
    """Update reorder level for warehouse-product combo."""
    try:
        async with container.uow() as uow:
            repo = SqlAlchemyWarehouseProductAssignmentRepository(uow)
            handler = UpdateReorderLevelCommandHandler(repo, uow)

        cmd = UpdateReorderLevelCommand(
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            default_reorder_level=request.default_reorder_level,
        )

        result = await handler.handle(cmd)

        return WarehouseProductAssignmentResponse(
            id=result.id,
            warehouse_id=result.warehouse_id,
            product_id=result.product_id,
            is_available=result.is_available,
            default_reorder_level=result.default_reorder_level,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update reorder level",
        )


# ── Query APIs ────────────────────────────────────────────────────────────────

@router.get(
    "/{warehouse_id}/products",
    response_model=List[WarehouseProductAssignmentListResponse],
    summary="List warehouse products",
    description="Get all products assigned to a warehouse.",
)
async def list_warehouse_products(
    warehouse_id: uuid.UUID,
    available_only: bool = Query(
        default=True,
        description="Only return available products",
    ),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    container = Depends(get_container),
) -> List[WarehouseProductAssignmentListResponse]:
    """Get all products assigned to a warehouse."""
    try:
        async with container.uow() as uow:
            repo = SqlAlchemyWarehouseProductAssignmentRepository(uow)

            if available_only:
                assignments = await repo.get_products_for_warehouse(warehouse_id, tenant_id)
            else:
                assignments = await repo.get_all_for_warehouse(warehouse_id, tenant_id)

        return [
            WarehouseProductAssignmentListResponse(
                id=str(a.id),
                warehouse_id=str(a.warehouse_id),
                product_id=str(a.product_id),
                is_available=a.is_available,
                default_reorder_level=a.default_reorder_level,
            )
            for a in assignments
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list warehouse products",
        )


@router.get(
    "/products/{product_id}/available-warehouses",
    response_model=List[AvailableWarehouseResponse],
    summary="Find available warehouses for product",
    description="Get all warehouses that have a specific product available.",
)
async def get_available_warehouses_for_product(
    product_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    container = Depends(get_container),
) -> List[AvailableWarehouseResponse]:
    """Get all warehouses that have a product available."""
    try:
        async with container.uow() as uow:
            repo = SqlAlchemyWarehouseProductAssignmentRepository(uow)

            assignments = await repo.get_warehouses_for_product(product_id, tenant_id)

        return [
            AvailableWarehouseResponse(
                warehouse_id=str(a.warehouse_id),
                warehouse_name="",  # Would be populated with actual warehouse data
                is_available=a.is_available,
                default_reorder_level=a.default_reorder_level,
            )
            for a in assignments
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get available warehouses",
        )
