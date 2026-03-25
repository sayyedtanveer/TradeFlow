import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel

from backend.app.application.bom.commands.routing_commands import AddWorkstationCommand
from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id
from backend.app.interfaces.api.v1.schemas.routing_schemas import WorkstationCreate, WorkstationResponse

from backend.app.interfaces.api.v1.dependencies.auth import get_container
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.infrastructure.persistence.repositories.bom_repository import BOMRepository
from backend.app.infrastructure.persistence.repositories.workstation_repository import WorkstationRepository
from backend.app.infrastructure.persistence.repositories.operation_repository import OperationRepository
from backend.app.application.bom.handlers.routing_handlers import RoutingHandlers

router = APIRouter(prefix="/workstations", tags=["Manufacturing Routing"])

@router.post("", response_model=uuid.UUID, status_code=status.HTTP_201_CREATED)
async def create_workstation(
    request: Request,
    body: WorkstationCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handlers = RoutingHandlers(uow, BOMRepository(session), WorkstationRepository(uow), OperationRepository(uow))

        cmd = AddWorkstationCommand(
            tenant_id=tenant_id,
            **body.model_dump()
        )
        return await handlers.handle_add_workstation(cmd)

@router.get("", response_model=List[WorkstationResponse])
async def list_workstations(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handlers = RoutingHandlers(uow, BOMRepository(session), WorkstationRepository(uow), OperationRepository(uow))
        workstations = await handlers._workstation_repo.list_workstations(tenant_id)
    return workstations
