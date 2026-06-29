"""Warehouse Management API routes.

Implements CRUD, user assignment, and warehouse view endpoints.
RBAC: Restricted to Admin role for management operations.
Requirements: 4.1, 4.2, 4.3, 4.4, 2.1
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.app.application.warehouse.commands import (
    AssignUserToWarehouseCommand,
    CreateWarehouseCommand,
    DeactivateWarehouseCommand,
    RemoveUserFromWarehouseCommand,
    UpdateWarehouseCommand,
)
from backend.app.application.warehouse.command_handlers import (
    AssignUserToWarehouseCommandHandler,
    CreateWarehouseCommandHandler,
    DeactivateWarehouseCommandHandler,
    RemoveUserFromWarehouseCommandHandler,
    UpdateWarehouseCommandHandler,
)
from backend.app.application.warehouse.queries import (
    GetWarehouseInventoryQuery,
    GetWarehouseOrdersQuery,
    GetWarehouseQuery,
    ListWarehousesQuery,
)
from backend.app.application.warehouse.query_handlers import (
    GetWarehouseInventoryQueryHandler,
    GetWarehouseOrdersQueryHandler,
    GetWarehouseQueryHandler,
    ListWarehousesQueryHandler,
)
from backend.app.infrastructure.persistence.repositories.warehouse_repository import (
    SqlAlchemyWarehouseRepository,
)
from backend.app.infrastructure.persistence.repositories.warehouse_user_assignment_repository import (
    SqlAlchemyWarehouseUserAssignmentRepository,
)
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_tenant_id,
    get_current_user_id,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.interfaces.api.v1.schemas.warehouse_schemas import (
    AssignUserRequest,
    CreateWarehouseRequest,
    UpdateWarehouseRequest,
    UserAssignmentResponse,
    WarehouseInventoryResponse,
    WarehouseListResponse,
    WarehouseOrdersResponse,
    WarehouseResponse,
)

router = APIRouter(prefix="/warehouses", tags=["Warehouses"])


def _error_status(message: str) -> int:
    """Map domain error messages to HTTP status codes."""
    normalized = message.lower()
    if "not found" in normalized:
        return status.HTTP_404_NOT_FOUND
    if "already exists" in normalized or "already inactive" in normalized:
        return status.HTTP_409_CONFLICT
    return status.HTTP_400_BAD_REQUEST


# ── Warehouse CRUD ─────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=WarehouseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new warehouse",
    dependencies=[Depends(require_permission("warehouse:write"))],
)
async def create_warehouse(
    body: CreateWarehouseRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Create a warehouse profile. Admin only."""
    container = get_container(request)
    async with container.session_factory() as session:
        warehouse_repo = SqlAlchemyWarehouseRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = CreateWarehouseCommandHandler(warehouse_repo=warehouse_repo)

        try:
            warehouse_id = await handler.handle(
                CreateWarehouseCommand(
                    tenant_id=tenant_id,
                    name=body.name,
                    address_street=body.address.street,
                    address_city=body.address.city,
                    address_region=body.address.region,
                    address_postal_code=body.address.postal_code,
                    address_country=body.address.country,
                    phone=body.phone,
                    email=body.email,
                    created_by=user_id,
                )
            )
            await uow.commit()
        except ValueError as e:
            raise HTTPException(status_code=_error_status(str(e)), detail=str(e))

        # Fetch the created warehouse for response
        query_handler = GetWarehouseQueryHandler(warehouse_repo=warehouse_repo)
        result = await query_handler.handle(
            GetWarehouseQuery(tenant_id=tenant_id, warehouse_id=warehouse_id)
        )

    return WarehouseResponse(**result)


@router.get(
    "",
    response_model=WarehouseListResponse,
    summary="List warehouses",
    dependencies=[Depends(require_permission("warehouse:read"))],
)
async def list_warehouses(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List all warehouses for the tenant with pagination."""
    container = get_container(request)
    async with container.session_factory() as session:
        warehouse_repo = SqlAlchemyWarehouseRepository(session)
        handler = ListWarehousesQueryHandler(warehouse_repo=warehouse_repo)
        result = await handler.handle(
            ListWarehousesQuery(
                tenant_id=tenant_id,
                is_active=is_active,
                page=page,
                page_size=page_size,
            )
        )

    return WarehouseListResponse(
        items=[WarehouseResponse(**w) for w in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
    summary="Get warehouse details",
    dependencies=[Depends(require_permission("warehouse:read"))],
)
async def get_warehouse(
    warehouse_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get details for a single warehouse."""
    container = get_container(request)
    async with container.session_factory() as session:
        warehouse_repo = SqlAlchemyWarehouseRepository(session)
        handler = GetWarehouseQueryHandler(warehouse_repo=warehouse_repo)
        try:
            result = await handler.handle(
                GetWarehouseQuery(tenant_id=tenant_id, warehouse_id=warehouse_id)
            )
        except ValueError as e:
            raise HTTPException(status_code=_error_status(str(e)), detail=str(e))

    return WarehouseResponse(**result)


@router.put(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
    summary="Update warehouse",
    dependencies=[Depends(require_permission("warehouse:write"))],
)
async def update_warehouse(
    warehouse_id: uuid.UUID,
    body: UpdateWarehouseRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update a warehouse profile. Admin only."""
    container = get_container(request)
    async with container.session_factory() as session:
        warehouse_repo = SqlAlchemyWarehouseRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = UpdateWarehouseCommandHandler(warehouse_repo=warehouse_repo)

        try:
            await handler.handle(
                UpdateWarehouseCommand(
                    tenant_id=tenant_id,
                    warehouse_id=warehouse_id,
                    updated_by=user_id,
                    name=body.name,
                    address_street=body.address_street,
                    address_city=body.address_city,
                    address_region=body.address_region,
                    address_postal_code=body.address_postal_code,
                    address_country=body.address_country,
                    phone=body.phone,
                    email=body.email,
                )
            )
            await uow.commit()
        except ValueError as e:
            raise HTTPException(status_code=_error_status(str(e)), detail=str(e))

        # Fetch updated warehouse
        query_handler = GetWarehouseQueryHandler(warehouse_repo=warehouse_repo)
        result = await query_handler.handle(
            GetWarehouseQuery(tenant_id=tenant_id, warehouse_id=warehouse_id)
        )

    return WarehouseResponse(**result)


@router.patch(
    "/{warehouse_id}/deactivate",
    response_model=WarehouseResponse,
    summary="Deactivate warehouse",
    dependencies=[Depends(require_permission("warehouse:write"))],
)
async def deactivate_warehouse(
    warehouse_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Deactivate a warehouse. Prevents new order assignments. Admin only."""
    container = get_container(request)
    async with container.session_factory() as session:
        warehouse_repo = SqlAlchemyWarehouseRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = DeactivateWarehouseCommandHandler(warehouse_repo=warehouse_repo)

        try:
            await handler.handle(
                DeactivateWarehouseCommand(
                    tenant_id=tenant_id,
                    warehouse_id=warehouse_id,
                    deactivated_by=user_id,
                )
            )
            await uow.commit()
        except ValueError as e:
            raise HTTPException(status_code=_error_status(str(e)), detail=str(e))

        # Fetch updated warehouse
        query_handler = GetWarehouseQueryHandler(warehouse_repo=warehouse_repo)
        result = await query_handler.handle(
            GetWarehouseQuery(tenant_id=tenant_id, warehouse_id=warehouse_id)
        )

    return WarehouseResponse(**result)


# ── User Assignment ────────────────────────────────────────────────────────────


@router.post(
    "/{warehouse_id}/users",
    response_model=UserAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign user to warehouse",
    dependencies=[Depends(require_permission("warehouse:write"))],
)
async def assign_user_to_warehouse(
    warehouse_id: uuid.UUID,
    body: AssignUserRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Assign a user to this warehouse.
    If the user is already assigned elsewhere, the previous assignment is revoked.
    Admin only.
    """
    container = get_container(request)
    async with container.session_factory() as session:
        warehouse_repo = SqlAlchemyWarehouseRepository(session)
        assignment_repo = SqlAlchemyWarehouseUserAssignmentRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = AssignUserToWarehouseCommandHandler(
            warehouse_repo=warehouse_repo,
            assignment_repo=assignment_repo,
        )

        try:
            assignment_id = await handler.handle(
                AssignUserToWarehouseCommand(
                    tenant_id=tenant_id,
                    warehouse_id=warehouse_id,
                    user_id=body.user_id,
                    assigned_by=user_id,
                )
            )
            await uow.commit()
        except ValueError as e:
            raise HTTPException(status_code=_error_status(str(e)), detail=str(e))

        # Fetch assignment for response
        assignment = await assignment_repo.get_by_user_id(
            tenant_id=tenant_id,
            user_id=body.user_id,
        )

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assignment created but could not be retrieved",
        )

    return UserAssignmentResponse(
        id=str(assignment.id),
        warehouse_id=str(assignment.warehouse_id),
        user_id=str(assignment.user_id),
        assigned_at=assignment.assigned_at.isoformat(),
        assigned_by=str(assignment.assigned_by),
    )


@router.delete(
    "/{warehouse_id}/users/{target_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove user from warehouse",
    dependencies=[Depends(require_permission("warehouse:write"))],
)
async def remove_user_from_warehouse(
    warehouse_id: uuid.UUID,
    target_user_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Remove a user's warehouse assignment. Admin only."""
    container = get_container(request)
    async with container.session_factory() as session:
        assignment_repo = SqlAlchemyWarehouseUserAssignmentRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = RemoveUserFromWarehouseCommandHandler(assignment_repo=assignment_repo)

        try:
            await handler.handle(
                RemoveUserFromWarehouseCommand(
                    tenant_id=tenant_id,
                    warehouse_id=warehouse_id,
                    user_id=target_user_id,
                    removed_by=user_id,
                )
            )
            await uow.commit()
        except ValueError as e:
            raise HTTPException(status_code=_error_status(str(e)), detail=str(e))


# ── Warehouse View Endpoints ──────────────────────────────────────────────────


@router.get(
    "/{warehouse_id}/inventory",
    response_model=WarehouseInventoryResponse,
    summary="Get warehouse inventory",
    dependencies=[Depends(require_permission("warehouse:read"))],
)
async def get_warehouse_inventory(
    warehouse_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Get inventory items for a specific warehouse."""
    container = get_container(request)
    async with container.session_factory() as session:
        warehouse_repo = SqlAlchemyWarehouseRepository(session)
        handler = GetWarehouseInventoryQueryHandler(warehouse_repo=warehouse_repo)

        try:
            result = await handler.handle(
                GetWarehouseInventoryQuery(
                    tenant_id=tenant_id,
                    warehouse_id=warehouse_id,
                    page=page,
                    page_size=page_size,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=_error_status(str(e)), detail=str(e))

    return WarehouseInventoryResponse(**result)


@router.get(
    "/{warehouse_id}/orders",
    response_model=WarehouseOrdersResponse,
    summary="Get warehouse orders",
    dependencies=[Depends(require_permission("warehouse:read"))],
)
async def get_warehouse_orders(
    warehouse_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    order_status: Optional[str] = Query(None, alias="status", description="Filter by order status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Get orders assigned to a specific warehouse."""
    container = get_container(request)
    async with container.session_factory() as session:
        warehouse_repo = SqlAlchemyWarehouseRepository(session)
        handler = GetWarehouseOrdersQueryHandler(warehouse_repo=warehouse_repo)

        try:
            result = await handler.handle(
                GetWarehouseOrdersQuery(
                    tenant_id=tenant_id,
                    warehouse_id=warehouse_id,
                    status=order_status,
                    page=page,
                    page_size=page_size,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=_error_status(str(e)), detail=str(e))

    return WarehouseOrdersResponse(**result)
