"""SQLAlchemy implementation of WarehouseUserAssignmentRepository."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Type

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.warehouse.entities.warehouse_user_assignment import (
    WarehouseUserAssignment,
)
from backend.app.domain.warehouse.repositories.warehouse_user_assignment_repository import (
    WarehouseUserAssignmentRepository,
)
from backend.app.infrastructure.persistence.models.warehouse_model import (
    WarehouseUserAssignmentModel,
)
from backend.app.infrastructure.persistence.repositories.base_repository import (
    BaseRepository,
)


class SqlAlchemyWarehouseUserAssignmentRepository(
    BaseRepository[WarehouseUserAssignment, WarehouseUserAssignmentModel]
):
    """Concrete SQLAlchemy-based implementation of WarehouseUserAssignmentRepository."""

    def _model_class(self) -> Type[WarehouseUserAssignmentModel]:
        return WarehouseUserAssignmentModel

    def _to_entity(self, model: WarehouseUserAssignmentModel) -> WarehouseUserAssignment:
        """Convert ORM model → WarehouseUserAssignment domain entity."""
        return WarehouseUserAssignment(
            id=model.id,
            tenant_id=model.tenant_id,
            user_id=model.user_id,
            warehouse_id=model.warehouse_id,
            assigned_at=model.assigned_at,
            assigned_by=model.assigned_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: WarehouseUserAssignment) -> WarehouseUserAssignmentModel:
        """Convert WarehouseUserAssignment domain entity → ORM model."""
        return WarehouseUserAssignmentModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            user_id=entity.user_id,
            warehouse_id=entity.warehouse_id,
            assigned_at=entity.assigned_at,
            assigned_by=entity.assigned_by,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def get_by_user_id(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[WarehouseUserAssignment]:
        """
        Return the current active assignment for a user.

        A user can only have one active assignment at a time.
        """
        stmt = select(WarehouseUserAssignmentModel).where(
            WarehouseUserAssignmentModel.tenant_id == tenant_id,
            WarehouseUserAssignmentModel.user_id == user_id,
            WarehouseUserAssignmentModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def find_by_warehouse(
        self, tenant_id: uuid.UUID, warehouse_id: uuid.UUID
    ) -> List[WarehouseUserAssignment]:
        """Return all user assignments for a given warehouse."""
        stmt = select(WarehouseUserAssignmentModel).where(
            WarehouseUserAssignmentModel.tenant_id == tenant_id,
            WarehouseUserAssignmentModel.warehouse_id == warehouse_id,
            WarehouseUserAssignmentModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def delete_by_user_id(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """
        Remove all assignments for a user (soft-delete).

        Used during reassignment to revoke the previous warehouse assignment.
        """
        stmt = (
            update(WarehouseUserAssignmentModel)
            .where(
                WarehouseUserAssignmentModel.tenant_id == tenant_id,
                WarehouseUserAssignmentModel.user_id == user_id,
                WarehouseUserAssignmentModel.is_deleted.is_(False),
            )
            .values(
                is_deleted=True,
                deleted_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        await self._session.execute(stmt)
