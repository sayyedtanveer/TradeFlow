"""Admin Order Management API routes.

Provides admin endpoints for:
  - View all orders with allocation status
  - Allocate orders to warehouses
  - Manually assign/reassign orders
  - View order details with fulfillment info
"""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.app.application.sales.command_handlers.order_allocation_handlers import (
    AllocateOrderCommandHandler,
    AssignOrderToWarehouseCommandHandler,
    ReassignOrderToWarehouseCommandHandler,
    ReleaseOrderFromWarehouseCommandHandler,
)
from backend.app.application.sales.commands.order_allocation_commands import (
    AllocateOrderCommand,
    AssignOrderToWarehouseCommand,
    ReassignOrderToWarehouseCommand,
    ReleaseOrderFromWarehouseCommand,
    OrderLineItemData,
)
from backend.app.application.sales.services.order_allocation_service import (
    OrderAllocationService,
)
from backend.app.domain.sales.repositories.sales_order_repository import (
    SalesOrderRepository,
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
from backend.app.interfaces.api.v1.schemas.admin_order_schemas import (
    AdminOrderResponse,
    AdminOrderListResponse,
    AllocateOrderRequest,
    AssignOrderToWarehouseRequest,
    ReassignOrderToWarehouseRequest,
    OrderAllocationResponse,
)

router = APIRouter(
    prefix="/admin/orders",
    tags=["Admin Order Management"],
)


# ── List Orders ────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=List[AdminOrderListResponse],
    summary="List all orders (admin view)",
    description="Get all orders with allocation status - admin view only.",
)
async def list_all_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: str = Query(
        None,
        description="Filter by order status (e.g., PENDING_INVENTORY_VALIDATION)",
    ),
    allocated_only: bool = Query(False, description="Only show allocated orders"),
    unallocated_only: bool = Query(False, description="Only show unallocated orders"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    container = Depends(get_container),
    _: None = Depends(require_permission("admin:view_orders")),
) -> List[AdminOrderListResponse]:
    """Get all orders with admin filters."""
    try:
        async with container.uow() as uow:
            sales_order_repo: SalesOrderRepository = container.sales_order_repository(uow)

            # Get orders - Note: You'd need to implement these query methods in the repository
            # For now, returning empty list as placeholder
            # In real implementation: query by status, pagination, allocation status

            return []

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list orders",
        )


@router.get(
    "/{order_id}",
    response_model=AdminOrderResponse,
    summary="Get order details (admin view)",
    description="Get complete order details including allocation info.",
)
async def get_order_details(
    order_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    container = Depends(get_container),
    _: None = Depends(require_permission("admin:view_orders")),
) -> AdminOrderResponse:
    """Get order details with allocation info."""
    try:
        async with container.uow() as uow:
            sales_order_repo: SalesOrderRepository = container.sales_order_repository(uow)

            order = await sales_order_repo.get_by_id(order_id, tenant_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order {order_id} not found",
            )

        # Map order to response - placeholder implementation
        return AdminOrderResponse(
            id=str(order.id),
            order_number=str(order.order_number),
            client_id=str(order.client_id),
            order_date=order.order_date,
            delivery_date=order.delivery_date,
            status=str(order.status),
            payment_status=str(order.payment_status),
            subtotal=order.subtotal,
            discount_amount=order.discount_amount,
            tax_amount=order.tax_amount,
            grand_total=order.grand_total,
            notes=order.notes,
            assigned_warehouse_id=str(order.assigned_warehouse_id) if order.assigned_warehouse_id else None,
            assigned_at=order.assigned_at,
            created_at=order.created_at,
            updated_at=order.updated_at,
            line_items=[],  # Would be populated from actual line items
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get order details",
        )


# ── Auto-Allocate Order ────────────────────────────────────────────────────────

@router.post(
    "/{order_id}/auto-allocate",
    response_model=OrderAllocationResponse,
    summary="Auto-allocate order to warehouse",
    description="Find and assign the best warehouse to fulfill this order.",
)
async def auto_allocate_order(
    order_id: uuid.UUID,
    request: AllocateOrderRequest,
    req: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    container = Depends(get_container),
    _: None = Depends(require_permission("admin:allocate_orders")),
) -> OrderAllocationResponse:
    """Auto-allocate an order to a suitable warehouse."""
    try:
        async with container.uow() as uow:
            warehouse_product_repo = SqlAlchemyWarehouseProductAssignmentRepository(uow)
            allocation_service = OrderAllocationService(warehouse_product_repo, uow)
            sales_order_repo: SalesOrderRepository = container.sales_order_repository(uow)

            # Create command with line items
            line_items = [
                OrderLineItemData(
                    product_id=item.product_id,
                    quantity=item.quantity,
                )
                for item in request.line_items
            ]

            cmd = AllocateOrderCommand(
                tenant_id=tenant_id,
                order_id=order_id,
                line_items=line_items,
                exclude_warehouse_ids=request.exclude_warehouses,
            )

            handler = AllocateOrderCommandHandler(allocation_service, sales_order_repo, uow)
            result = await handler.handle(cmd)

            return OrderAllocationResponse(
                order_id=result.order_id,
                allocated_warehouse_id=result.allocated_warehouse_id,
                status=result.status,
                message=result.message,
                allocated_at=None,  # Would be set from the updated order
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to allocate order",
        )


# ── Manually Assign Order ──────────────────────────────────────────────────────

@router.post(
    "/{order_id}/assign-warehouse",
    response_model=OrderAllocationResponse,
    summary="Manually assign order to warehouse",
    description="Override auto-allocation and assign order to specific warehouse.",
)
async def assign_order_to_warehouse(
    order_id: uuid.UUID,
    request: AssignOrderToWarehouseRequest,
    req: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    container = Depends(get_container),
    _: None = Depends(require_permission("admin:allocate_orders")),
) -> OrderAllocationResponse:
    """Manually assign an order to a specific warehouse."""
    try:
        async with container.uow() as uow:
            sales_order_repo: SalesOrderRepository = container.sales_order_repository(uow)

            cmd = AssignOrderToWarehouseCommand(
            tenant_id=tenant_id,
            order_id=order_id,
            warehouse_id=request.warehouse_id,
            assigned_by=user_id,
        )

        handler = AssignOrderToWarehouseCommandHandler(sales_order_repo, uow)
        result = await handler.handle(cmd)

        return OrderAllocationResponse(
            order_id=result.order_id,
            allocated_warehouse_id=result.allocated_warehouse_id,
            status=result.status,
            message=result.message,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign order",
        )


# ── Reassign Order ─────────────────────────────────────────────────────────────

@router.post(
    "/{order_id}/reassign-warehouse",
    response_model=OrderAllocationResponse,
    summary="Reassign order to different warehouse",
    description="Move order from current warehouse to another (e.g., when inventory unavailable).",
)
async def reassign_order_to_warehouse(
    order_id: uuid.UUID,
    request: ReassignOrderToWarehouseRequest,
    req: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    container = Depends(get_container),
    _: None = Depends(require_permission("admin:allocate_orders")),
) -> OrderAllocationResponse:
    """Reassign an order to a different warehouse."""
    try:
        async with container.uow() as uow:
            sales_order_repo: SalesOrderRepository = container.sales_order_repository(uow)

            cmd = ReassignOrderToWarehouseCommand(
            tenant_id=tenant_id,
            order_id=order_id,
            new_warehouse_id=request.warehouse_id,
            reason=request.reason,
            reassigned_by=user_id,
        )

        handler = ReassignOrderToWarehouseCommandHandler(sales_order_repo, uow)
        result = await handler.handle(cmd)

        return OrderAllocationResponse(
            order_id=result.order_id,
            allocated_warehouse_id=result.allocated_warehouse_id,
            status=result.status,
            message=result.message,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reassign order",
        )


# ── Release Order ──────────────────────────────────────────────────────────────

@router.post(
    "/{order_id}/release-warehouse",
    response_model=OrderAllocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Release order from warehouse",
    description="Remove warehouse assignment (undo allocation).",
)
async def release_order_from_warehouse(
    order_id: uuid.UUID,
    reason: str = Query(None, description="Reason for release"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    container = Depends(get_container),
    _: None = Depends(require_permission("admin:allocate_orders")),
) -> OrderAllocationResponse:
    """Release an order from its warehouse."""
    try:
        async with container.uow() as uow:
            sales_order_repo: SalesOrderRepository = container.sales_order_repository(uow)

            cmd = ReleaseOrderFromWarehouseCommand(
            tenant_id=tenant_id,
            order_id=order_id,
            reason=reason,
        )

        handler = ReleaseOrderFromWarehouseCommandHandler(sales_order_repo, uow)
        result = await handler.handle(cmd)

        return OrderAllocationResponse(
            order_id=result.order_id,
            allocated_warehouse_id="",
            status=result.status,
            message=result.message,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to release order",
        )
