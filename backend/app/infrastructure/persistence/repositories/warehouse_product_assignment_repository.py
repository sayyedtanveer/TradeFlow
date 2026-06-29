"""SQLAlchemy Repository Implementation for Warehouse-Product Assignment."""

from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import and_, select

from backend.app.domain.warehouse.entities.warehouse_product_assignment import (
    WarehouseProductAssignment,
)
from backend.app.domain.warehouse.repositories.warehouse_product_assignment_repository import (
    WarehouseProductAssignmentRepository,
)
from backend.app.infrastructure.persistence.models.warehouse_model import (
    WarehouseProductAssignmentModel,
)
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork


class SqlAlchemyWarehouseProductAssignmentRepository(
    WarehouseProductAssignmentRepository
):
    """SQLAlchemy implementation of WarehouseProductAssignmentRepository."""

    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self._uow = uow

    async def get_by_id(
        self, id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[WarehouseProductAssignment]:
        """Return assignment by ID or None (excludes soft-deleted)."""
        stmt = select(WarehouseProductAssignmentModel).where(
            and_(
                WarehouseProductAssignmentModel.id == id,
                WarehouseProductAssignmentModel.tenant_id == tenant_id,
                WarehouseProductAssignmentModel.is_deleted == False,
            )
        )
        result = await self._uow.session.execute(stmt)
        model = result.scalars().first()
        return self._model_to_entity(model) if model else None

    async def get_by_warehouse_and_product(
        self,
        warehouse_id: uuid.UUID,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Optional[WarehouseProductAssignment]:
        """Return assignment for specific warehouse-product combo."""
        stmt = select(WarehouseProductAssignmentModel).where(
            and_(
                WarehouseProductAssignmentModel.warehouse_id == warehouse_id,
                WarehouseProductAssignmentModel.product_id == product_id,
                WarehouseProductAssignmentModel.tenant_id == tenant_id,
                WarehouseProductAssignmentModel.is_deleted == False,
            )
        )
        result = await self._uow.session.execute(stmt)
        model = result.scalars().first()
        return self._model_to_entity(model) if model else None

    async def get_warehouses_for_product(
        self, product_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> List[WarehouseProductAssignment]:
        """Return all warehouses that carry this product (only available=True)."""
        stmt = select(WarehouseProductAssignmentModel).where(
            and_(
                WarehouseProductAssignmentModel.product_id == product_id,
                WarehouseProductAssignmentModel.tenant_id == tenant_id,
                WarehouseProductAssignmentModel.is_available == True,
                WarehouseProductAssignmentModel.is_deleted == False,
            )
        )
        result = await self._uow.session.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(m) for m in models]

    async def get_products_for_warehouse(
        self, warehouse_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> List[WarehouseProductAssignment]:
        """Return all products assigned to this warehouse (only available=True)."""
        stmt = select(WarehouseProductAssignmentModel).where(
            and_(
                WarehouseProductAssignmentModel.warehouse_id == warehouse_id,
                WarehouseProductAssignmentModel.tenant_id == tenant_id,
                WarehouseProductAssignmentModel.is_available == True,
                WarehouseProductAssignmentModel.is_deleted == False,
            )
        )
        result = await self._uow.session.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(m) for m in models]

    async def get_all_for_warehouse(
        self, warehouse_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> List[WarehouseProductAssignment]:
        """Return all assignments for warehouse, including unavailable."""
        stmt = select(WarehouseProductAssignmentModel).where(
            and_(
                WarehouseProductAssignmentModel.warehouse_id == warehouse_id,
                WarehouseProductAssignmentModel.tenant_id == tenant_id,
                WarehouseProductAssignmentModel.is_deleted == False,
            )
        )
        result = await self._uow.session.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(m) for m in models]

    async def save(
        self, entity: WarehouseProductAssignment
    ) -> WarehouseProductAssignment:
        """Insert or update the assignment."""
        model = await self._get_or_create_model(entity.id)
        model.warehouse_id = entity.warehouse_id
        model.product_id = entity.product_id
        model.tenant_id = entity.tenant_id
        model.is_available = entity.is_available
        model.default_reorder_level = entity.default_reorder_level
        model.created_at = entity.created_at
        model.updated_at = entity.updated_at
        model.is_deleted = entity.is_deleted
        model.deleted_at = entity.deleted_at

        self._uow.session.add(model)
        await self._uow.session.flush()
        return self._model_to_entity(model)

    async def delete(self, id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        """Soft-delete the assignment."""
        stmt = select(WarehouseProductAssignmentModel).where(
            and_(
                WarehouseProductAssignmentModel.id == id,
                WarehouseProductAssignmentModel.tenant_id == tenant_id,
                WarehouseProductAssignmentModel.is_deleted == False,
            )
        )
        result = await self._uow.session.execute(stmt)
        model = result.scalars().first()
        if model:
            from datetime import datetime, timezone
            model.is_deleted = True
            model.deleted_at = datetime.now(timezone.utc)
            self._uow.session.add(model)
            await self._uow.session.flush()

    async def _get_or_create_model(
        self, id: Optional[uuid.UUID]
    ) -> WarehouseProductAssignmentModel:
        """Get existing model or create new one."""
        if id:
            stmt = select(WarehouseProductAssignmentModel).where(
                WarehouseProductAssignmentModel.id == id
            )
            result = await self._uow.session.execute(stmt)
            model = result.scalars().first()
            if model:
                return model
        return WarehouseProductAssignmentModel()

    @staticmethod
    def _model_to_entity(
        model: WarehouseProductAssignmentModel,
    ) -> WarehouseProductAssignment:
        """Convert SQLAlchemy model to domain entity."""
        return WarehouseProductAssignment(
            id=model.id,
            tenant_id=model.tenant_id,
            warehouse_id=model.warehouse_id,
            product_id=model.product_id,
            is_available=model.is_available,
            default_reorder_level=model.default_reorder_level,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
        )
