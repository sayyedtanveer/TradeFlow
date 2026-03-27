"""Sales Order Repository."""

from datetime import date
from typing import Type
from uuid import UUID

from sqlalchemy import select, func

from backend.app.domain.sales.entities.sales_order import SalesOrder
from backend.app.domain.sales.value_objects import OrderStatus
from backend.app.infrastructure.persistence.models.sales_models import SalesOrderModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository


class SalesOrderRepository(BaseRepository):
    """Repository for SalesOrder aggregate root."""

    def _model_class(self) -> Type[SalesOrderModel]:
        """Return the SQLAlchemy model class."""
        return SalesOrderModel

    def _to_entity(self, model: SalesOrderModel) -> SalesOrder:
        """Convert ORM model → domain entity."""
        if not model:
            return None
        return SalesOrder(
            id=model.id,
            tenant_id=model.tenant_id,
            order_number=model.order_number,
            client_id=model.client_id,
            order_date=model.order_date,
            delivery_date=model.delivery_date,
            status=OrderStatus(model.status),
            subtotal=model.subtotal,
            discount_amount=model.discount_amount,
            tax_amount=model.tax_amount,
            grand_total=model.grand_total,
            notes=model.notes,
            created_by=model.created_by,
            is_active=model.is_active,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: SalesOrder) -> SalesOrderModel:
        """Convert domain entity → ORM model."""
        return SalesOrderModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            order_number=entity.order_number,
            client_id=entity.client_id,
            order_date=entity.order_date,
            delivery_date=entity.delivery_date,
            status=entity.status.value,
            subtotal=entity.subtotal,
            discount_amount=entity.discount_amount,
            tax_amount=entity.tax_amount,
            grand_total=entity.grand_total,
            notes=entity.notes,
            created_by=entity.created_by,
            is_active=entity.is_active,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def get_by_order_number(
        self,
        tenant_id: UUID,
        order_number: str,
    ) -> SalesOrder | None:
        """
        Get order by order number (unique per tenant).
        
        Args:
            tenant_id: Tenant ID
            order_number: Order number string
            
        Returns:
            SalesOrder or None if not found
        """
        stmt = (
            select(self._model_class())
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().order_number == order_number,
                self._model_class().is_active.is_(True),
                self._model_class().is_deleted.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def find_by_client(
        self,
        tenant_id: UUID,
        client_id: UUID,
        status: OrderStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SalesOrder]:
        """
        Find orders for a client.
        
        Args:
            tenant_id: Tenant ID
            client_id: Client ID
            status: Filter by status (optional)
            limit: Result limit
            offset: Result offset
            
        Returns:
            List of sales orders
        """
        stmt = (
            select(self._model_class())
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().client_id == client_id,
                self._model_class().is_active.is_(True),
                self._model_class().is_deleted.is_(False),
            )
        )
        
        if status:
            stmt = stmt.where(self._model_class().status == status.value)
        
        stmt = stmt.order_by(self._model_class().order_date.desc())
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def find_by_date_range(
        self,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
        status: OrderStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SalesOrder]:
        """
        Find orders within date range.
        
        Args:
            tenant_id: Tenant ID
            start_date: Start date
            end_date: End date
            status: Filter by status (optional)
            limit: Result limit
            offset: Result offset
            
        Returns:
            List of sales orders
        """
        stmt = (
            select(self._model_class())
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().order_date >= str(start_date),
                self._model_class().order_date <= str(end_date),
                self._model_class().is_active.is_(True),
                self._model_class().is_deleted.is_(False),
            )
        )
        
        if status:
            stmt = stmt.where(self._model_class().status == status.value)
        
        stmt = stmt.order_by(self._model_class().order_date.desc())
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def find_by_delivery_date_range(
        self,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
        statuses: list[OrderStatus] | None = None,
    ) -> list[SalesOrder]:
        """
        Find orders due for delivery within date range.
        
        Args:
            tenant_id: Tenant ID
            start_date: Start delivery date
            end_date: End delivery date
            statuses: List of statuses to filter (optional)
            
        Returns:
            List of sales orders
        """
        stmt = (
            select(self._model_class())
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().delivery_date >= str(start_date),
                self._model_class().delivery_date <= str(end_date),
                self._model_class().is_active.is_(True),
                self._model_class().is_deleted.is_(False),
            )
        )
        
        if statuses:
            status_values = [s.value for s in statuses]
            stmt = stmt.where(self._model_class().status.in_(status_values))
        
        stmt = stmt.order_by(self._model_class().delivery_date.asc())
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def count_by_status(
        self,
        tenant_id: UUID,
    ) -> dict[str, int]:
        """
        Count orders by status.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Dictionary mapping status to count
        """
        stmt = (
            select(
                self._model_class().status,
                func.count(self._model_class().id).label("count")
            )
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().is_active.is_(True),
                self._model_class().is_deleted.is_(False),
            )
            .group_by(self._model_class().status)
        )
        
        result = await self._session.execute(stmt)
        rows = result.all()
        return {status: count for status, count in rows}

    async def find_pending_confirmation(
        self,
        tenant_id: UUID,
        limit: int = 50,
    ) -> list[SalesOrder]:
        """
        Find orders in DRAFT status waiting for confirmation.
        
        Args:
            tenant_id: Tenant ID
            limit: Result limit
            
        Returns:
            List of draft orders
        """
        stmt = (
            select(self._model_class())
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().status == OrderStatus.DRAFT.value,
                self._model_class().is_active.is_(True),
                self._model_class().is_deleted.is_(False),
            )
            .order_by(self._model_class().created_at.asc())
            .limit(limit)
        )
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]


