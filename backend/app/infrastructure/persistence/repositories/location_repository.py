from typing import Type

from backend.app.domain.inventory.entities.location import Location, LocationType
from backend.app.infrastructure.persistence.models.location_model import LocationModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository

class LocationRepository(BaseRepository[Location, LocationModel]):
    def _model_class(self) -> Type[LocationModel]:
        return LocationModel

    def _to_entity(self, model: LocationModel) -> Location:
        entity = Location(
            id=model.id,
            tenant_id=model.tenant_id,
            name=model.name,
            location_type=LocationType(model.type),
            parent_location_id=model.parent_location_id,
            code=model.code,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
        entity._is_deleted = model.is_deleted
        entity._deleted_at = model.deleted_at
        return entity

    def _to_model(self, entity: Location) -> LocationModel:
        return LocationModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            name=entity.name,
            code=entity.code,
            type=entity.location_type.value if hasattr(entity.location_type, "value") else entity.location_type,
            parent_location_id=entity.parent_location_id,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
        )
