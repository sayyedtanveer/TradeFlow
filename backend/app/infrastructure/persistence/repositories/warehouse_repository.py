"""SQLAlchemy implementation of WarehouseRepository."""

from __future__ import annotations

import uuid
from typing import List, Optional, Type

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.warehouse.entities.warehouse import Warehouse
from backend.app.domain.warehouse.repositories.warehouse_repository import (
    WarehouseRepository,
)
from backend.app.domain.warehouse.value_objects.address import Address
from backend.app.infrastructure.persistence.models.warehouse_model import (
    WarehouseModel,
)
from backend.app.infrastructure.persistence.repositories.base_repository import (
    BaseRepository,
)


class SqlAlchemyWarehouseRepository(BaseRepository[Warehouse, WarehouseModel]):
    """Concrete SQLAlchemy-based implementation of WarehouseRepository."""

    def _model_class(self) -> Type[WarehouseModel]:
        return WarehouseModel

    def _to_entity(self, model: WarehouseModel) -> Warehouse:
        """Convert ORM model → Warehouse domain entity."""
        address = Address(
            street=model.address_street,
            city=model.address_city,
            region=model.address_region,
            postal_code=model.address_postal_code,
            country=model.address_country,
        )
        return Warehouse(
            id=model.id,
            tenant_id=model.tenant_id,
            name=model.name,
            address=address,
            phone=model.phone,
            email=model.email,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: Warehouse) -> WarehouseModel:
        """Convert Warehouse domain entity → ORM model."""
        return WarehouseModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            name=entity.name,
            address_street=entity.address.street,
            address_city=entity.address.city,
            address_region=entity.address.region,
            address_postal_code=entity.address.postal_code,
            address_country=entity.address.country,
            phone=entity.phone,
            email=entity.email,
            is_active=entity.is_active,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def get_by_name(
        self, tenant_id: uuid.UUID, name: str
    ) -> Optional[Warehouse]:
        """Return warehouse by name within a tenant (for uniqueness checks)."""
        stmt = select(WarehouseModel).where(
            WarehouseModel.tenant_id == tenant_id,
            WarehouseModel.name == name,
            WarehouseModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list(
        self,
        tenant_id: uuid.UUID,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[Warehouse]:
        """Return paginated list of warehouses, optionally filtered by is_active."""
        offset = (page - 1) * page_size
        stmt = select(WarehouseModel).where(
            WarehouseModel.tenant_id == tenant_id,
            WarehouseModel.is_deleted.is_(False),
        )
        if is_active is not None:
            stmt = stmt.where(WarehouseModel.is_active == is_active)
        stmt = stmt.offset(offset).limit(page_size).order_by(
            WarehouseModel.created_at.desc()
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count(
        self,
        tenant_id: uuid.UUID,
        is_active: Optional[bool] = None,
    ) -> int:
        """Return total count of warehouses matching filters."""
        stmt = (
            select(func.count())
            .select_from(WarehouseModel)
            .where(
                WarehouseModel.tenant_id == tenant_id,
                WarehouseModel.is_deleted.is_(False),
            )
        )
        if is_active is not None:
            stmt = stmt.where(WarehouseModel.is_active == is_active)
        result = await self._session.execute(stmt)
        return result.scalar_one()
