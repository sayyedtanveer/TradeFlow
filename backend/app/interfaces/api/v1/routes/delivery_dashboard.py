"""Delivery Dashboard REST API endpoints."""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Request, status

from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_current_user_id
from backend.app.interfaces.api.v1.dependencies.auth import get_container
from backend.app.application.delivery.commands.delivery_commands import (
    CreateDispatchCommand,
    UpdateShipmentStatusCommand,
    PackDeliveryCommand,
    ConfirmDeliveryCommand,
)
from backend.app.application.delivery.handlers.delivery_dashboard_handler import DeliveryDashboardHandler


router = APIRouter(prefix="/delivery", tags=["Delivery Dashboard"])


@router.get("/dispatch-queue")
async def get_dispatch_queue(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get dispatch queue for delivery dashboard."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.delivery.services.delivery_dashboard_service import DeliveryDashboardService
        service = DeliveryDashboardService(session)
        queue = await service.get_dispatch_queue(tenant_id=tenant_id)
        return queue


@router.get("/in-transit-queue")
async def get_in_transit_queue(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get in-transit shipments for delivery dashboard."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.delivery.services.delivery_dashboard_service import DeliveryDashboardService
        service = DeliveryDashboardService(session)
        queue = await service.get_in_transit_queue(tenant_id=tenant_id)
        return queue


@router.get("/delivered-queue")
async def get_delivered_queue(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get delivered orders for delivery dashboard."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.delivery.services.delivery_dashboard_service import DeliveryDashboardService
        service = DeliveryDashboardService(session)
        queue = await service.get_delivered_queue(tenant_id=tenant_id)
        return queue


@router.post("/create-dispatch", status_code=status.HTTP_200_OK)
async def create_dispatch(
    body: CreateDispatchCommand,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Create dispatch for delivery order."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = DeliveryDashboardHandler(session)
        cmd = CreateDispatchCommand(
            tenant_id=tenant_id,
            delivery_order_id=body.delivery_order_id,
            shipped_by=user_id,
            tracking_number=body.tracking_number,
            remarks=body.remarks,
        )
        await handler.handle_create_dispatch(cmd)
        await session.commit()
        return {"status": "IN_TRANSIT"}


@router.post("/pack", status_code=status.HTTP_200_OK)
async def pack_delivery(
    body: PackDeliveryCommand,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Pack delivery order for shipment."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = DeliveryDashboardHandler(session)
        cmd = PackDeliveryCommand(
            tenant_id=tenant_id,
            delivery_order_id=body.delivery_order_id,
            packed_by=user_id,
            packing_notes=body.packing_notes,
        )
        await handler.handle_pack_delivery(cmd)
        await session.commit()
        return {"status": "PACKING"}


@router.post("/update-shipment-status", status_code=status.HTTP_200_OK)
async def update_shipment_status(
    body: UpdateShipmentStatusCommand,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update shipment status."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = DeliveryDashboardHandler(session)
        cmd = UpdateShipmentStatusCommand(
            tenant_id=tenant_id,
            delivery_order_id=body.delivery_order_id,
            new_status=body.new_status,
            updated_by=user_id,
            remarks=body.remarks,
        )
        await handler.handle_update_shipment_status(cmd)
        await session.commit()
        return {"status": "success"}


@router.post("/confirm-delivery", status_code=status.HTTP_200_OK)
async def confirm_delivery(
    body: ConfirmDeliveryCommand,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Confirm delivery of order."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = DeliveryDashboardHandler(session)
        cmd = ConfirmDeliveryCommand(
            tenant_id=tenant_id,
            delivery_order_id=body.delivery_order_id,
            confirmed_by=user_id,
            delivery_notes=body.delivery_notes,
        )
        await handler.handle_confirm_delivery(cmd)
        await session.commit()
        return {"status": "DELIVERED"}
