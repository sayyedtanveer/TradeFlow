"""Work Order & Shop Floor REST API endpoints."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import JSONResponse

from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_current_user_id
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.interfaces.api.v1.schemas.work_order_schemas import (
    WorkOrderCreateRequest, IssueMaterialRequest, RecordProductionRequest,
    StartJobCardRequest, CompleteJobCardRequest,
    WorkOrderSummary, WorkOrderDetail, JobCardResponse, WorkOrderErrorResponse,
    MaterialAvailabilityResponse,
)
from backend.app.application.manufacturing.commands.work_order_commands import (
    CreateWorkOrderCommand, ReleaseWorkOrderCommand, StartWorkOrderCommand,
    IssueMaterialCommand, RecordProductionCommand,
    CompleteWorkOrderCommand, CloseWorkOrderCommand,
    StartJobCardCommand, CompleteJobCardCommand,
)
from backend.app.application.manufacturing.commands.worker_commands import (
    StartOperationCommand, PauseOperationCommand, CompleteOperationCommand, ReportWastageCommand,
)
from backend.app.application.manufacturing.handlers.work_order_handler import WorkOrderHandler
from backend.app.application.manufacturing.handlers.worker_handler import WorkerHandler
from backend.app.application.manufacturing.services.material_availability_service import (
    MaterialAvailabilityService,
)
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.domain.manufacturing.exceptions import (
    InsufficientStockError, MaterialNotIssuedError, BOMNotFoundError, WorkOrderImmutableError
)
from backend.app.domain.manufacturing.entities.work_order import InvalidStatusTransitionError

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend.app.infrastructure.persistence.models.work_order_model import (
    WorkOrderModel, JobCardModel
)
from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.interfaces.api.v1.dependencies.auth import get_container


router = APIRouter(prefix="/work-orders", tags=["Work Orders"])


def _get_handler(request: Request):
    container = get_container(request)
    return container.session_factory


async def _error_response(exc: Exception) -> JSONResponse:
    """Map domain exceptions to structured error payloads."""
    code = getattr(exc, "error_code", "INTERNAL_ERROR")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error_code": code, "message": str(exc), "validation_errors": []},
    )


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("manufacturing:write"))])
async def create_work_order(
    body: WorkOrderCreateRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        try:
            cmd = CreateWorkOrderCommand(
                tenant_id=tenant_id, created_by=user_id, **body.model_dump()
            )
            wo_id = await handler.handle_create(cmd)
            await uow.commit()
            return {"id": str(wo_id)}
        except (BOMNotFoundError, ValueError) as e:
            return await _error_response(e)


@router.get("", response_model=List[WorkOrderSummary], dependencies=[Depends(require_permission("manufacturing:read"))])
async def list_work_orders(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    status_filter: Optional[str] = Query(None, alias="status"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    product_id: Optional[uuid.UUID] = Query(None),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = select(WorkOrderModel).where(
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        )
        if status_filter:
            stmt = stmt.where(WorkOrderModel.status == status_filter)
        if product_id:
            stmt = stmt.where(WorkOrderModel.product_id == product_id)
        stmt = stmt.order_by(WorkOrderModel.created_at.desc())
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [WorkOrderSummary.model_validate(r) for r in rows]


@router.get(
    "/material-availability",
    response_model=MaterialAvailabilityResponse,
    dependencies=[Depends(require_permission("manufacturing:read"))],
)
async def preview_material_availability(
    request: Request,
    product_id: uuid.UUID = Query(...),
    quantity: Decimal = Query(..., gt=0),
    bom_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        service = MaterialAvailabilityService(session)
        try:
            preview = await service.check_material_availability(
                tenant_id=tenant_id,
                product_id=product_id,
                quantity=quantity,
                bom_id=bom_id,
            )
            return MaterialAvailabilityResponse.model_validate(preview)
        except BOMNotFoundError as exc:
            return await _error_response(exc)


@router.get("/{work_order_id}", response_model=WorkOrderDetail, dependencies=[Depends(require_permission("manufacturing:read"))])
async def get_work_order(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(WorkOrderModel)
            .options(
                selectinload(WorkOrderModel.materials),
                selectinload(WorkOrderModel.job_cards),
            )
            .where(
                WorkOrderModel.id == work_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
        )
        result = await session.execute(stmt)
        wo = result.scalar_one_or_none()
        if not wo:
            return JSONResponse(status_code=404, content={"error_code": "NOT_FOUND", "message": "Work Order not found", "validation_errors": []})
        return WorkOrderDetail.model_validate(wo)


@router.post("/{work_order_id}/release", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("manufacturing:write"))])
async def release_work_order(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        try:
            await handler.handle_release(ReleaseWorkOrderCommand(tenant_id=tenant_id, work_order_id=work_order_id))
            await uow.commit()
            return {"status": "RELEASED"}
        except InvalidStatusTransitionError as e:
            return await _error_response(e)


@router.post("/{work_order_id}/start", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("manufacturing:write"))])
async def start_work_order(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        try:
            await handler.handle_start(StartWorkOrderCommand(tenant_id=tenant_id, work_order_id=work_order_id))
            await uow.commit()
            return {"status": "IN_PROGRESS"}
        except InvalidStatusTransitionError as e:
            return await _error_response(e)


@router.post("/{work_order_id}/issue-materials", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("manufacturing:write"))])
async def issue_materials(
    work_order_id: uuid.UUID,
    body: IssueMaterialRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        try:
            cmd = IssueMaterialCommand(
                tenant_id=tenant_id, work_order_id=work_order_id, issued_by=user_id, **body.model_dump()
            )
            await handler.handle_issue_material(cmd)
            await uow.commit()
            return {"message": "Material issued"}
        except (InsufficientStockError, InvalidStatusTransitionError, ValueError) as e:
            return await _error_response(e)


@router.post("/{work_order_id}/record-production", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("manufacturing:write"))])
async def record_production(
    work_order_id: uuid.UUID,
    body: RecordProductionRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        try:
            cmd = RecordProductionCommand(
                tenant_id=tenant_id, work_order_id=work_order_id, recorded_by=user_id, **body.model_dump()
            )
            await handler.handle_record_production(cmd)
            await uow.commit()
            return {"message": "Production recorded"}
        except (InsufficientStockError, ValueError) as e:
            return await _error_response(e)


@router.post("/{work_order_id}/complete", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("manufacturing:write"))])
async def complete_work_order(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        try:
            await handler.handle_complete(CompleteWorkOrderCommand(tenant_id=tenant_id, work_order_id=work_order_id))
            await uow.commit()
            return {"status": "COMPLETED"}
        except (InvalidStatusTransitionError, MaterialNotIssuedError) as e:
            return await _error_response(e)


@router.post("/{work_order_id}/close", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("manufacturing:write"))])
async def close_work_order(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        try:
            await handler.handle_close(CloseWorkOrderCommand(tenant_id=tenant_id, work_order_id=work_order_id))
            await uow.commit()
            return {"status": "CLOSED"}
        except InvalidStatusTransitionError as e:
            return await _error_response(e)


@router.get("/{work_order_id}/job-cards", response_model=List[JobCardResponse], dependencies=[Depends(require_permission("manufacturing:read"))])
async def list_job_cards(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(JobCardModel)
            .join(WorkOrderModel, JobCardModel.work_order_id == WorkOrderModel.id)
            .where(
                JobCardModel.work_order_id == work_order_id,
                WorkOrderModel.tenant_id == tenant_id,
            )
            .order_by(JobCardModel.sequence)
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()
        
        # Build response with operation_name from relationship
        job_cards_data = []
        for jc in rows:
            job_cards_data.append({
                "id": str(jc.id),
                "operation_id": str(jc.operation_id),
                "operation_name": jc.operation.name if jc.operation else "",
                "sequence": jc.sequence,
                "status": jc.status,
                "assigned_to": str(jc.assigned_to) if jc.assigned_to else None,
                "started_at": jc.started_at.isoformat() if jc.started_at else None,
                "completed_at": jc.completed_at.isoformat() if jc.completed_at else None,
                "remarks": jc.remarks,
            })
        return job_cards_data


@router.patch("/{work_order_id}/job-cards/{job_card_id}/start", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("manufacturing:write"))])
async def start_job_card(
    work_order_id: uuid.UUID,
    job_card_id: uuid.UUID,
    body: StartJobCardRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        try:
            cmd = StartJobCardCommand(
                tenant_id=tenant_id, work_order_id=work_order_id,
                job_card_id=job_card_id, **body.model_dump()
            )
            await handler.handle_start_job_card(cmd)
            await uow.commit()
            return {"status": "IN_PROGRESS"}
        except ValueError as e:
            return await _error_response(e)


@router.get("/{work_order_id}/material-consumption", dependencies=[Depends(require_permission("manufacturing:read"))])
async def get_work_order_consumption(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get the material consumption history for this Work Order."""
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(InventoryTransactionModel, MaterialModel.code, MaterialModel.name)
            .join(MaterialModel, MaterialModel.id == InventoryTransactionModel.material_id)
            .where(
                InventoryTransactionModel.tenant_id == tenant_id,
                InventoryTransactionModel.reference_type == "work_order",
                InventoryTransactionModel.reference_id == work_order_id,
                InventoryTransactionModel.transaction_type == "issue",
                InventoryTransactionModel.is_deleted.is_(False),
            )
            .order_by(InventoryTransactionModel.created_at.desc())
        )
        result = await session.execute(stmt)
        rows = result.all()

    return [
        {
            "id": str(tx.id),
            "material_id": str(tx.material_id),
            "material_code": code,
            "material_name": name,
            "quantity": float(tx.quantity),
            "created_at": tx.created_at.isoformat(),
            "remarks": tx.remarks,
        }
        for tx, code, name in rows
    ]
@router.patch("/{work_order_id}/job-cards/{job_card_id}/complete", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("manufacturing:write"))])
async def complete_job_card(
    work_order_id: uuid.UUID,
    job_card_id: uuid.UUID,
    body: CompleteJobCardRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        try:
            cmd = CompleteJobCardCommand(
                tenant_id=tenant_id, work_order_id=work_order_id,
                job_card_id=job_card_id, **body.model_dump()
            )
            await handler.handle_complete_job_card(cmd)
            await uow.commit()
            return {"status": "DONE"}
        except ValueError as e:
            return await _error_response(e)


# ── Phase 4: Worker Operational Flow ───────────────────────────────────────

@router.get("/worker/queue")
async def get_worker_queue(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get assigned work orders and operations for worker dashboard."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.manufacturing.services.production_execution_service import ProductionExecutionService
        service = ProductionExecutionService(session)
        queue = await service.get_worker_queue(tenant_id=tenant_id, user_id=user_id)
        return queue


@router.post("/{work_order_id}/job-cards/{job_card_id}/start-operation", status_code=status.HTTP_200_OK)
async def start_operation(
    work_order_id: uuid.UUID,
    job_card_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Start a job card operation."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = WorkerHandler(session)
        cmd = StartOperationCommand(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            job_card_id=job_card_id,
            assigned_to=user_id,
        )
        await handler.handle_start_operation(cmd)
        await session.commit()
        return {"status": "IN_PROGRESS"}


@router.post("/{work_order_id}/job-cards/{job_card_id}/pause-operation", status_code=status.HTTP_200_OK)
async def pause_operation(
    work_order_id: uuid.UUID,
    job_card_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Pause a job card operation."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = WorkerHandler(session)
        cmd = PauseOperationCommand(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            job_card_id=job_card_id,
        )
        await handler.handle_pause_operation(cmd)
        await session.commit()
        return {"status": "PAUSED"}


@router.post("/{work_order_id}/job-cards/{job_card_id}/complete-operation", status_code=status.HTTP_200_OK)
async def complete_operation(
    work_order_id: uuid.UUID,
    job_card_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Complete a job card operation."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = WorkerHandler(session)
        cmd = CompleteOperationCommand(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            job_card_id=job_card_id,
        )
        await handler.handle_complete_operation(cmd)
        await session.commit()
        return {"status": "DONE"}


@router.post("/{work_order_id}/report-wastage", status_code=status.HTTP_200_OK)
async def report_wastage(
    work_order_id: uuid.UUID,
    body: dict,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Report scrap/wastage during production."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = WorkerHandler(session)
        cmd = ReportWastageCommand(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            scrap_quantity=Decimal(str(body.get("scrap_quantity", 0))),
            recorded_by=user_id,
            notes=body.get("notes"),
        )
        await handler.handle_report_wastage(cmd)
        await session.commit()
        return {"status": "success"}


# ── Phase 5: QC Operational Flow ─────────────────────────────────────────

@router.get("/qc/inspection-queue")
async def get_inspection_queue(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get QC inspection queue for QC dashboard."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.quality.services.qc_service import QCService
        service = QCService(session)
        queue = await service.get_inspection_queue(tenant_id=tenant_id)
        return queue


@router.get("/qc/rejected-queue")
async def get_rejected_queue(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get rejected batches for QC dashboard."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.quality.services.qc_service import QCService
        service = QCService(session)
        queue = await service.get_rejected_queue(tenant_id=tenant_id)
        return queue


@router.get("/qc/rework-queue")
async def get_rework_queue(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get rework queue for QC dashboard."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.quality.services.qc_service import QCService
        service = QCService(session)
        queue = await service.get_rework_queue(tenant_id=tenant_id)
        return queue


@router.post("/{work_order_id}/qc/approve", status_code=status.HTTP_200_OK)
async def qc_approve(
    work_order_id: uuid.UUID,
    body: dict,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Approve QC inspection."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = WorkOrderHandler(session)
        cmd = QCApproveCommand(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            approved_by=user_id,
            remarks=body.get("remarks"),
        )
        await handler.handle_qc_approve(cmd)
        await session.commit()
        return {"status": "QC_APPROVED"}


@router.post("/{work_order_id}/qc/reject", status_code=status.HTTP_200_OK)
async def qc_reject(
    work_order_id: uuid.UUID,
    body: dict,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Reject QC inspection."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = WorkOrderHandler(session)
        cmd = QCRejectCommand(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            rejected_by=user_id,
            reason=body.get("reason", ""),
            send_to_rework=body.get("send_to_rework", False),
        )
        await handler.handle_qc_reject(cmd)
        await session.commit()
        return {"status": "QC_REJECTED"}


@router.post("/{work_order_id}/qc/send-to-rework", status_code=status.HTTP_200_OK)
async def qc_send_to_rework(
    work_order_id: uuid.UUID,
    body: dict,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Send rejected WO to rework."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = WorkOrderHandler(session)
        cmd = QCSendToReworkCommand(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            sent_by=user_id,
            remarks=body.get("remarks"),
        )
        await handler.handle_qc_send_to_rework(cmd)
        await session.commit()
        return {"status": "REWORK"}


@router.post("/{work_order_id}/fg-receive", status_code=status.HTTP_200_OK)
async def fg_receive(
    work_order_id: uuid.UUID,
    body: dict,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Receive finished goods after QC approval."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = WorkOrderHandler(session)
        cmd = FGReceiveCommand(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            received_by=user_id,
            remarks=body.get("remarks"),
        )
        await handler.handle_fg_receive(cmd)
        await session.commit()
        return {"status": "FG_RECEIVED"}


