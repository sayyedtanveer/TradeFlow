"""SQLAlchemy implementation for WarehouseProductThreshold persistence."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Type

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.warehouse.entities.warehouse_product_threshold import (
    WarehouseProductThreshold,
)
from backend.app.infrastructure.persistence.models.warehouse_model import (
    WarehouseProductThresholdModel,
)
from backend.app.infrastructure.persistence.repositories.base_repository import (
    BaseRepository,
)


class SqlAlchemyWarehouseProductThresholdRepository(
    BaseRepository[WarehouseProductThreshold, WarehouseProductThresholdModel]
):
    """Concrete SQLAlchemy-based repository for WarehouseProductThreshold entities."""

    def _model_class(self) -> Type[WarehouseProductThresholdModel]:
        return WarehouseProductThresholdModel

    def _to_entity(self, model: WarehouseProductThresholdModel) -> WarehouseProductThreshold:
        """Convert ORM model → WarehouseProductThreshold domain entity."""
        return WarehouseProductThreshold(
            id=model.id,
            tenant_id=model.tenant_id,
            warehouse_id=model.warehouse_id,
            product_id=model.product_id,
            reorder_threshold=model.reorder_threshold,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: WarehouseProductThreshold) -> WarehouseProductThresholdModel:
        """Convert WarehouseProductThreshold domain entity → ORM model."""
        return WarehouseProductThresholdModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            warehouse_id=entity.warehouse_id,
            product_id=entity.product_id,
            reorder_threshold=entity.reorder_threshold,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def get_by_warehouse_and_product(
        self,
        tenant_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        product_id: uuid.UUID,
    ) -> Optional[WarehouseProductThreshold]:
        """Return threshold for a specific warehouse-product pair."""
        stmt = select(WarehouseProductThresholdModel).where(
            WarehouseProductThresholdModel.tenant_id == tenant_id,
            WarehouseProductThresholdModel.warehouse_id == warehouse_id,
            WarehouseProductThresholdModel.product_id == product_id,
            WarehouseProductThresholdModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def find_by_warehouse(
        self,
        tenant_id: uuid.UUID,
        warehouse_id: uuid.UUID,
    ) -> List[WarehouseProductThreshold]:
        """Return all thresholds for a given warehouse."""
        stmt = select(WarehouseProductThresholdModel).where(
            WarehouseProductThresholdModel.tenant_id == tenant_id,
            WarehouseProductThresholdModel.warehouse_id == warehouse_id,
            WarehouseProductThresholdModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def find_by_product(
        self,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
    ) -> List[WarehouseProductThreshold]:
        """Return all thresholds for a given product across warehouses."""
        stmt = select(WarehouseProductThresholdModel).where(
            WarehouseProductThresholdModel.tenant_id == tenant_id,
            WarehouseProductThresholdModel.product_id == product_id,
            WarehouseProductThresholdModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]
