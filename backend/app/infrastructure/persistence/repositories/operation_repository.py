import uuid
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.domain.bom.entities.operation import Operation
from backend.app.infrastructure.persistence.models.operation_model import OperationModel
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork


class OperationRepository:
    def __init__(self, uow: SQLAlchemyUnitOfWork):
        self._uow = uow

    @property
    def _session(self):
        return self._uow._session

    def _to_entity(self, model: OperationModel) -> Operation:
        return Operation(
            id=model.id,
            tenant_id=model.tenant_id,
            name=model.name,
            workstation_id=model.workstation_id,
            setup_time=float(model.setup_time),
            run_time=float(model.run_time),
            description=model.description,
            is_active=model.is_active,
            is_deleted=model.is_deleted,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Operation) -> OperationModel:
        return OperationModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            name=entity.name,
            workstation_id=entity.workstation_id,
            setup_time=entity.setup_time,
            run_time=entity.run_time,
            description=entity.description,
            is_active=entity.is_active,
            is_deleted=entity.is_deleted,
        )

    async def get_by_id(self, operation_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Operation]:
        stmt = select(OperationModel).where(
            OperationModel.id == operation_id,
            OperationModel.tenant_id == tenant_id,
            OperationModel.is_deleted.is_(False)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_operations(self, tenant_id: uuid.UUID) -> List[Operation]:
        stmt = select(OperationModel).where(
            OperationModel.tenant_id == tenant_id,
            OperationModel.is_deleted.is_(False)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    def save(self, operation: Operation) -> None:
        model = self._to_model(operation)
        self._session.add(model)
