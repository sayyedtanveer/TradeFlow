"""Storekeeper dashboard API routes."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.logging.logger import get_logger
from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_current_user_id
from backend.app.application.inventory.services.storekeeper_service import StorekeeperService
from backend.app.application.inventory.handlers.storekeeper_handler import StorekeeperHandler
from backend.app.application.inventory.commands.storekeeper_commands import (
    ReserveStockCommand,
    IssueMaterialCommand,
    PartialIssueCommand,
    RejectIssueCommand,
    ReturnMaterialCommand,
)
from backend.app.interfaces.api.v1.schemas.storekeeper_schemas import (
    IssueQueueResponse,
    ShortageQueueResponse,
    PartiallyIssuedWOResponse,
    ReserveStockRequest,
    IssueMaterialRequest,
    PartialIssueRequest,
    RejectIssueRequest,
    ReturnMaterialRequest,
)

logger = get_logger(__name__)


async def _get_db_session(request: Request):
    factory = request.app.state.container.session_factory
    async with factory() as session:
        yield session

router = APIRouter(prefix="/storekeeper", tags=["Storekeeper"])


# ── Storekeeper Dashboard Queues ────────────────────────────────────────────────

@router.get("/issue-queue", response_model=list[IssueQueueResponse])
async def get_issue_queue(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Get material issue queue for storekeeper dashboard.
    
    Shows all pending material issues.
    """
    logger.info("Storekeeper issue-queue endpoint called", extra={"tenant_id": str(tenant_id)})
    storekeeper_service = StorekeeperService(session)
    queue = await storekeeper_service.get_issue_queue(tenant_id=tenant_id)
    logger.info("Storekeeper issue-queue returned data", extra={"queue_size": len(queue)})
    return queue


@router.get("/shortage-queue", response_model=list[ShortageQueueResponse])
async def get_shortage_queue(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Get shortage queue for storekeeper dashboard.
    
    Shows all material shortages.
    """
    storekeeper_service = StorekeeperService(session)
    queue = await storekeeper_service.get_shortage_queue(tenant_id=tenant_id)
    return queue


@router.get("/partially-issued-wo", response_model=list[PartiallyIssuedWOResponse])
async def get_partially_issued_wo(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Get partially issued WOs for storekeeper dashboard.
    
    Shows WOs with partial material issues.
    """
    storekeeper_service = StorekeeperService(session)
    queue = await storekeeper_service.get_partially_issued_wo(tenant_id=tenant_id)
    return queue


# ── Storekeeper Actions ─────────────────────────────────────────────────────────

@router.post("/reserve-stock")
async def reserve_stock(
    body: ReserveStockRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    reserved_by: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Reserve stock for Work Order.
    
    Triggers WO transition: MATERIAL_PENDING → MATERIAL_RESERVED.
    Inventory: AVAILABLE → RESERVED.
    """
    command = ReserveStockCommand(
        tenant_id=tenant_id,
        work_order_id=body.work_order_id,
        material_id=body.material_id,
        quantity=body.quantity,
        unit_id=body.unit_id,
        reserved_by=reserved_by,
    )
    
    handler = StorekeeperHandler(session)
    await handler.handle_reserve_stock(command)
    
    await session.commit()
    return {"status": "success", "message": "Stock reserved"}


@router.post("/issue-material")
async def issue_material(
    body: IssueMaterialRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    issued_by: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Issue reserved stock to Work Order.
    
    Triggers WO transition: MATERIAL_RESERVED → MATERIAL_ISSUED.
    Inventory: RESERVED → ISSUED.
    """
    command = IssueMaterialCommand(
        tenant_id=tenant_id,
        work_order_id=body.work_order_id,
        material_id=body.material_id,
        quantity=body.quantity,
        unit_id=body.unit_id,
        issued_by=issued_by,
    )
    
    handler = StorekeeperHandler(session)
    await handler.handle_issue_material(command)
    
    await session.commit()
    return {"status": "success", "message": "Material issued"}


@router.post("/partial-issue")
async def partial_issue(
    body: PartialIssueRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    issued_by: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Partially issue stock to Work Order.
    
    WO stays in MATERIAL_RESERVED until all materials issued.
    """
    command = PartialIssueCommand(
        tenant_id=tenant_id,
        work_order_id=body.work_order_id,
        material_id=body.material_id,
        quantity=body.quantity,
        unit_id=body.unit_id,
        issued_by=issued_by,
    )
    
    handler = StorekeeperHandler(session)
    await handler.handle_partial_issue(command)
    
    await session.commit()
    return {"status": "success", "message": "Partial issue completed"}


@router.post("/reject-issue")
async def reject_issue(
    body: RejectIssueRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    rejected_by: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Reject material issue request.
    
    Cancels reservation and logs rejection reason.
    Inventory: RESERVED → AVAILABLE.
    """
    command = RejectIssueCommand(
        tenant_id=tenant_id,
        work_order_id=body.work_order_id,
        material_id=body.material_id,
        reason=body.reason,
        rejected_by=rejected_by,
    )
    
    handler = StorekeeperHandler(session)
    await handler.handle_reject_issue(command)
    
    await session.commit()
    return {"status": "success", "message": "Issue rejected"}


@router.post("/return-material")
async def return_material(
    body: ReturnMaterialRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    returned_by: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Return issued material back to inventory.
    
    Inventory: ISSUED → RESERVED.
    """
    command = ReturnMaterialCommand(
        tenant_id=tenant_id,
        work_order_id=body.work_order_id,
        material_id=body.material_id,
        quantity=body.quantity,
        unit_id=body.unit_id,
        returned_by=returned_by,
    )
    
    handler = StorekeeperHandler(session)
    await handler.handle_return_material(command)
    
    await session.commit()
    return {"status": "success", "message": "Material returned"}
