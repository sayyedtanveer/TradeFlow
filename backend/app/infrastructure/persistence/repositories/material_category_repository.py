from typing import Type

from backend.app.domain.inventory.entities.material_category import MaterialCategory
from backend.app.infrastructure.persistence.models.material_category_model import MaterialCategoryModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository

class MaterialCategoryRepository(BaseRepository[MaterialCategory, MaterialCategoryModel]):
    def _model_class(self) -> Type[MaterialCategoryModel]:
        return MaterialCategoryModel

    def _to_entity(self, model: MaterialCategoryModel) -> MaterialCategory:
        entity = MaterialCategory(
            id=model.id,
            tenant_id=model.tenant_id,
            name=model.name,
            description=model.description,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
        entity._is_deleted = model.is_deleted
        entity._deleted_at = model.deleted_at
        return entity

    def _to_model(self, entity: MaterialCategory) -> MaterialCategoryModel:
        return MaterialCategoryModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            name=entity.name,
            description=entity.description,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
        )
