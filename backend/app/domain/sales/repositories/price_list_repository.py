"""Price List Repository."""

from typing import Type
from uuid import UUID

from sqlalchemy import select

from backend.app.domain.sales.entities.price_list import PriceList
from backend.app.infrastructure.persistence.models.sales_models import PriceListModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository


class PriceListRepository(BaseRepository):
    """Repository for PriceList aggregate root."""

    def _model_class(self) -> Type[PriceListModel]:
        """Return the SQLAlchemy model class."""
        return PriceListModel

    def _to_entity(self, model: PriceListModel) -> PriceList:
        """Convert ORM model → domain entity."""
        if not model:
            return None
        return PriceList(
            id=model.id,
            tenant_id=model.tenant_id,
            name=model.name,
            is_default=model.is_default,
            is_active=model.is_active,
            valid_from=model.valid_from,
            valid_to=model.valid_to,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: PriceList) -> PriceListModel:
        """Convert domain entity → ORM model."""
        return PriceListModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            name=entity.name,
            is_default=entity.is_default,
            is_active=entity.is_active,
            valid_from=entity.valid_from,
            valid_to=entity.valid_to,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def find_default(
        self,
        tenant_id: UUID,
        include_inactive: bool = False,
    ) -> list[PriceList]:
        """
        Find default price lists for a tenant.
        
        Args:
            tenant_id: Tenant ID
            include_inactive: Whether to include inactive price lists
            
        Returns:
            List of default price lists
        """
        stmt = (
            select(self._model_class())
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().is_default.is_(True),
                self._model_class().is_deleted.is_(False),
            )
        )
        
        if not include_inactive:
            stmt = stmt.where(self._model_class().is_active.is_(True))
        
        stmt = stmt.order_by(self._model_class().valid_from.desc())
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def find_by_client(
        self,
        tenant_id: UUID,
        client_id: UUID,
        include_inactive: bool = False,
    ) -> list[PriceList]:
        """
        Find client-specific price lists.
        
        Note: This assumes there's a many-to-many relationship
        between PriceList and Client. Actual implementation
        would need a ClientPriceList junction table.
        
        Args:
            tenant_id: Tenant ID
            client_id: Client ID
            include_inactive: Whether to include inactive price lists
            
        Returns:
            List of price lists for this client
        """
        # This is a placeholder - actual implementation would need:
        # 1. A ClientPriceList mapping table
        # 2. A join query through that table
        # For now, returning empty to avoid errors
        return []

    async def find_by_name(
        self,
        tenant_id: UUID,
        name: str,
        include_inactive: bool = False,
    ) -> list[PriceList]:
        """
        Find price lists by name (case-insensitive).
        
        Args:
            tenant_id: Tenant ID
            name: Price list name (partial match)
            include_inactive: Whether to include inactive price lists
            
        Returns:
            List of matching price lists
        """
        stmt = (
            select(self._model_class())
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().name.ilike(f"%{name}%"),
                self._model_class().is_deleted.is_(False),
            )
        )
        
        if not include_inactive:
            stmt = stmt.where(self._model_class().is_active.is_(True))
        
        stmt = stmt.order_by(self._model_class().name.asc())
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def find_active_on_date(
        self,
        tenant_id: UUID,
        check_date,
        is_default: bool | None = None,
    ) -> list[PriceList]:
        """
        Find price lists active on a specific date.
        
        Args:
            tenant_id: Tenant ID
            check_date: Date to check (date object)
            is_default: Filter to default lists only (optional)
            
        Returns:
            List of active price lists on that date
        """
        stmt = (
            select(self._model_class())
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().is_active.is_(True),
                self._model_class().is_deleted.is_(False),
                self._model_class().valid_from <= check_date,
            )
        )
        
        # valid_to is NULL or >= check_date
        stmt = stmt.where(
            (self._model_class().valid_to.is_(None)) |
            (self._model_class().valid_to >= check_date)
        )
        
        if is_default is not None:
            stmt = stmt.where(self._model_class().is_default.is_(is_default))
        
        stmt = stmt.order_by(self._model_class().is_default.desc())
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]


