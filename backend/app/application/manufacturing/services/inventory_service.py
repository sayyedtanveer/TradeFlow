"""
InventoryService — canonical gateway for ALL stock mutations.

Rules:
  - ALL stock changes MUST go through this service.
  - Direct SQL stock updates or repository-level mutations are PROHIBITED.
  - SELECT FOR UPDATE is used for concurrency safety.
  - Negative stock is prevented.
  - Every mutation inserts an InventoryTransaction audit record.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
from backend.app.domain.manufacturing.exceptions import InsufficientStockError


class InventoryService:
    """Single authoritative point for stock reservation, issuance, and receipt."""

    def __init__(self, session: AsyncSession):
        self._session = session

    # ── Internal helper ────────────────────────────────────────────────────────

    async def _lock_material(self, tenant_id: uuid.UUID, material_id: uuid.UUID) -> MaterialModel:
        """Acquire a row-level lock (SELECT FOR UPDATE) on the material."""
        stmt = (
            select(MaterialModel)
            .where(MaterialModel.id == material_id, MaterialModel.tenant_id == tenant_id)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Material {material_id} not found for tenant {tenant_id}")
        return model

    async def _log_transaction(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        transaction_type: str,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        reference_type: str,
        reference_id: uuid.UUID,
        created_by: uuid.UUID,
        remarks: Optional[str] = None,
    ) -> None:
        tx = InventoryTransactionModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type=transaction_type,
            quantity=float(quantity),
            unit_id=unit_id,
            reference_type=reference_type,
            reference_id=reference_id,
            remarks=remarks,
            created_by=created_by,
        )
        self._session.add(tx)

    # ── Public API ──────────────────────────────────────────────────────────────

    async def reserve_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        work_order_id: uuid.UUID,
        unit_id: Optional[uuid.UUID] = None,
        created_by: uuid.UUID,
    ) -> None:
        """Reserve stock (soft lock) when WO is released. Non-destructive."""
        model = await self._lock_material(tenant_id, material_id)
        available = Decimal(str(model.current_stock)) - Decimal(str(model.reserved_stock))
        if quantity > available:
            raise InsufficientStockError(
                f"Cannot reserve {quantity}: only {available} available for {material_id}"
            )
        model.reserved_stock = float(Decimal(str(model.reserved_stock)) + quantity)
        await self._log_transaction(
            tenant_id=tenant_id, material_id=material_id, transaction_type="reserve",
            quantity=quantity, unit_id=unit_id, reference_type="work_order",
            reference_id=work_order_id, created_by=created_by,
            remarks=f"Reserved for WO {work_order_id}",
        )

    async def issue_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        work_order_id: uuid.UUID,
        unit_id: Optional[uuid.UUID] = None,
        created_by: uuid.UUID,
    ) -> None:
        """Physically issue material: decrease current_stock and reserved_stock."""
        model = await self._lock_material(tenant_id, material_id)
        current = Decimal(str(model.current_stock))
        if quantity > current:
            raise InsufficientStockError(
                f"Insufficient stock for {material_id}: requested {quantity}, available {current}"
            )
        model.current_stock = float(current - quantity)
        # Release reservation (capped to avoid going negative)
        reserved = Decimal(str(model.reserved_stock))
        model.reserved_stock = float(max(Decimal("0"), reserved - quantity))
        await self._log_transaction(
            tenant_id=tenant_id, material_id=material_id, transaction_type="issue",
            quantity=quantity, unit_id=unit_id, reference_type="work_order",
            reference_id=work_order_id, created_by=created_by,
            remarks=f"Issued for WO {work_order_id}",
        )

    async def receive_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        work_order_id: uuid.UUID,
        unit_id: Optional[uuid.UUID] = None,
        created_by: uuid.UUID,
    ) -> None:
        """Receive finished goods into stock after production."""
        model = await self._lock_material(tenant_id, material_id)
        model.current_stock = float(Decimal(str(model.current_stock)) + quantity)
        await self._log_transaction(
            tenant_id=tenant_id, material_id=material_id, transaction_type="produce",
            quantity=quantity, unit_id=unit_id, reference_type="work_order",
            reference_id=work_order_id, created_by=created_by,
            remarks=f"Production receipt for WO {work_order_id}",
        )
