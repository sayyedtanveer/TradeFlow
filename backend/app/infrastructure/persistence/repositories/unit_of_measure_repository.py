from typing import Type

from backend.app.domain.inventory.entities.unit_of_measure import UnitOfMeasure
from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository

class UnitOfMeasureRepository(BaseRepository[UnitOfMeasure, UnitOfMeasureModel]):
    def _model_class(self) -> Type[UnitOfMeasureModel]:
        return UnitOfMeasureModel

    def _to_entity(self, model: UnitOfMeasureModel) -> UnitOfMeasure:
        entity = UnitOfMeasure(
            id=model.id,
            tenant_id=model.tenant_id,
            code=model.code,
            name=model.name,
            precision=model.precision,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
        entity._is_deleted = model.is_deleted
        entity._deleted_at = model.deleted_at
        return entity

    def _to_model(self, entity: UnitOfMeasure) -> UnitOfMeasureModel:
        return UnitOfMeasureModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            code=entity.code,
            name=entity.name,
            precision=entity.precision,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
        )
