"""Work Order & Shop Floor REST API endpoints."""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import JSONResponse

from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_current_user_id
from backend.app.interfaces.api.v1.schemas.work_order_schemas import (
    WorkOrderCreateRequest, IssueMaterialRequest, RecordProductionRequest,
    StartJobCardRequest, CompleteJobCardRequest,
    WorkOrderSummary, WorkOrderDetail, JobCardResponse, WorkOrderErrorResponse,
)
from backend.app.application.manufacturing.commands.work_order_commands import (
    CreateWorkOrderCommand, ReleaseWorkOrderCommand, StartWorkOrderCommand,
    IssueMaterialCommand, RecordProductionCommand,
    CompleteWorkOrderCommand, CloseWorkOrderCommand,
    StartJobCardCommand, CompleteJobCardCommand,
)
from backend.app.application.manufacturing.handlers.work_order_handler import WorkOrderHandler
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


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_work_order(
    body: WorkOrderCreateRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session)
        try:
            cmd = CreateWorkOrderCommand(
                tenant_id=tenant_id, created_by=user_id, **body.model_dump()
            )
            wo_id = await handler.handle_create(cmd)
            await uow.commit()
            return {"id": str(wo_id)}
        except (BOMNotFoundError, ValueError) as e:
            return await _error_response(e)


@router.get("", response_model=List[WorkOrderSummary])
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


@router.get("/{work_order_id}", response_model=WorkOrderDetail)
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


@router.post("/{work_order_id}/release", status_code=status.HTTP_200_OK)
async def release_work_order(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session)
        try:
            await handler.handle_release(ReleaseWorkOrderCommand(tenant_id=tenant_id, work_order_id=work_order_id))
            await uow.commit()
            return {"status": "RELEASED"}
        except InvalidStatusTransitionError as e:
            return await _error_response(e)


@router.post("/{work_order_id}/start", status_code=status.HTTP_200_OK)
async def start_work_order(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session)
        try:
            await handler.handle_start(StartWorkOrderCommand(tenant_id=tenant_id, work_order_id=work_order_id))
            await uow.commit()
            return {"status": "IN_PROGRESS"}
        except InvalidStatusTransitionError as e:
            return await _error_response(e)


@router.post("/{work_order_id}/issue-materials", status_code=status.HTTP_200_OK)
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
        handler = WorkOrderHandler(session)
        try:
            cmd = IssueMaterialCommand(
                tenant_id=tenant_id, work_order_id=work_order_id, issued_by=user_id, **body.model_dump()
            )
            await handler.handle_issue_material(cmd)
            await uow.commit()
            return {"message": "Material issued"}
        except (InsufficientStockError, InvalidStatusTransitionError, ValueError) as e:
            return await _error_response(e)


@router.post("/{work_order_id}/record-production", status_code=status.HTTP_200_OK)
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
        handler = WorkOrderHandler(session)
        try:
            cmd = RecordProductionCommand(
                tenant_id=tenant_id, work_order_id=work_order_id, recorded_by=user_id, **body.model_dump()
            )
            await handler.handle_record_production(cmd)
            await uow.commit()
            return {"message": "Production recorded"}
        except (InsufficientStockError, ValueError) as e:
            return await _error_response(e)


@router.post("/{work_order_id}/complete", status_code=status.HTTP_200_OK)
async def complete_work_order(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session)
        try:
            await handler.handle_complete(CompleteWorkOrderCommand(tenant_id=tenant_id, work_order_id=work_order_id))
            await uow.commit()
            return {"status": "COMPLETED"}
        except (InvalidStatusTransitionError, MaterialNotIssuedError) as e:
            return await _error_response(e)


@router.post("/{work_order_id}/close", status_code=status.HTTP_200_OK)
async def close_work_order(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session)
        try:
            await handler.handle_close(CloseWorkOrderCommand(tenant_id=tenant_id, work_order_id=work_order_id))
            await uow.commit()
            return {"status": "CLOSED"}
        except InvalidStatusTransitionError as e:
            return await _error_response(e)


@router.get("/{work_order_id}/job-cards", response_model=List[JobCardResponse])
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
        return [JobCardResponse.model_validate(r) for r in rows]


@router.patch("/{work_order_id}/job-cards/{job_card_id}/start", status_code=status.HTTP_200_OK)
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
        handler = WorkOrderHandler(session)
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


@router.patch("/{work_order_id}/job-cards/{job_card_id}/complete", status_code=status.HTTP_200_OK)
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
        handler = WorkOrderHandler(session)
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
