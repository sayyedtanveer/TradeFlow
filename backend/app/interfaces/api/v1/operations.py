import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request

from backend.app.application.bom.commands.routing_commands import AddOperationCommand
from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id
from backend.app.interfaces.api.v1.schemas.routing_schemas import OperationCreate, OperationResponse

from backend.app.interfaces.api.v1.dependencies.auth import get_container
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.infrastructure.persistence.repositories.bom_repository import BOMRepository
from backend.app.infrastructure.persistence.repositories.workstation_repository import WorkstationRepository
from backend.app.infrastructure.persistence.repositories.operation_repository import OperationRepository
from backend.app.application.bom.handlers.routing_handlers import RoutingHandlers

router = APIRouter(prefix="/operations", tags=["Manufacturing Routing"])

@router.post("", response_model=uuid.UUID, status_code=status.HTTP_201_CREATED)
async def create_operation(
    request: Request,
    body: OperationCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handlers = RoutingHandlers(uow, BOMRepository(session), WorkstationRepository(uow), OperationRepository(uow))


        cmd = AddOperationCommand(
            tenant_id=tenant_id,
            **body.model_dump()
        )
        return await handlers.handle_add_operation(cmd)

@router.get("", response_model=List[OperationResponse])
async def list_operations(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handlers = RoutingHandlers(uow, BOMRepository(session), WorkstationRepository(uow), OperationRepository(uow))
        operations = await handlers._operation_repo.list_operations(tenant_id)
    return operations
