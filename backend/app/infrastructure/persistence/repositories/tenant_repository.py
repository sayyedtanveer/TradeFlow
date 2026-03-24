from __future__ import annotations

import uuid
from typing import Optional, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.tenant.entities.tenant import Tenant
from backend.app.domain.tenant.repositories.tenant_repository_interface import ITenantRepository
from backend.app.domain.tenant.value_objects.email import Email
from backend.app.domain.tenant.value_objects.role import Role
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository


class TenantRepository(BaseRepository[Tenant, TenantModel], ITenantRepository):

    def _model_class(self) -> Type[TenantModel]:
        return TenantModel

    def _to_entity(self, model: TenantModel) -> Tenant:
        return Tenant(
            id=model.id,
            tenant_id=model.id,
            name=model.name,
            slug=model.slug,
            plan=model.plan,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: Tenant) -> TenantModel:
        return TenantModel(
            id=entity.id,
            name=entity.name,
            slug=entity.slug,
            plan=entity.plan,
            is_active=entity.is_active,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def get_by_slug(self, slug: str) -> Optional[Tenant]:
        stmt = select(TenantModel).where(
            TenantModel.slug == slug,
            TenantModel.is_deleted.is_(False),
            TenantModel.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_tenant_id(self, tenant_id: uuid.UUID) -> Optional[Tenant]:
        """Fetch a tenant by its own primary key (id).

        The Tenant aggregate root has no separate tenant_id column — its id IS
        the tenant_id used for all child entities. This method bypasses the
        BaseRepository.get_by_id() which incorrectly filters on a non-existent
        tenant_id column.
        """
        stmt = select(TenantModel).where(
            TenantModel.id == tenant_id,
            TenantModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def slug_exists(self, slug: str) -> bool:
        stmt = select(TenantModel.id).where(TenantModel.slug == slug)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
