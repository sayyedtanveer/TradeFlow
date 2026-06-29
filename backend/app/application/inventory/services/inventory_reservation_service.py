"""Inventory Reservation Service - domain service for reservation lifecycle."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.inventory.services.stock_service import InventoryService
from backend.app.domain.inventory.entities.inventory_reservation import (
    InventoryReservation,
    ReservationStatus,
)


class InventoryReservationService:
    """Domain service for inventory reservation lifecycle management.

    Responsibilities:
    - Handle partial reservations
    - Track reservation states
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._inventory = InventoryService(session)

    async def get_reservation_audit_trail(
        self,
        *,
        tenant_id: uuid.UUID,
        reference_type: str,
        reference_id: uuid.UUID,
    ) -> list[InventoryReservation]:
        """Get full reservation audit trail for a reference."""
        from backend.app.infrastructure.persistence.models.inventory_reservation_model import (
            InventoryReservationModel,
        )

        stmt = (
            select(InventoryReservationModel)
            .where(
                InventoryReservationModel.tenant_id == tenant_id,
                InventoryReservationModel.reference_type == reference_type,
                InventoryReservationModel.reference_id == reference_id,
            )
            .order_by(InventoryReservationModel.created_at)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        reservations = []
        for model in models:
            reservations.append(
                InventoryReservation(
                    id=model.id,
                    tenant_id=model.tenant_id,
                    reference_type=model.reference_type,
                    reference_id=model.reference_id,
                    material_id=model.material_id,
                    batch_id=model.batch_id,
                    warehouse_id=getattr(model, 'warehouse_id', None),
                    order_id=getattr(model, 'order_id', None),
                    quantity=Decimal(str(model.quantity)),
                    status=ReservationStatus(model.status),
                    unit_id=model.unit_id,
                    issued_quantity=Decimal(str(model.issued_quantity or 0)),
                    consumed_quantity=Decimal(str(model.consumed_quantity or 0)),
                    returned_quantity=Decimal(str(model.returned_quantity or 0)),
                    created_at=model.created_at,
                    updated_at=model.updated_at,
                )
            )
        return reservations
