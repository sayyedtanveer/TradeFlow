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

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
from backend.app.infrastructure.persistence.models.inventory_management_models import StockLedgerModel
from backend.app.infrastructure.persistence.models.location_model import LocationModel
from backend.app.infrastructure.persistence.models.stock_level_model import StockLevelModel
from backend.app.domain.manufacturing.exceptions import InsufficientStockError

# Locations usable for internal manufacturing issue (not subcontractor / quarantine)
_INTERNAL_ISSUE_LOCATION_TYPES: frozenset[str] = frozenset(
    {"warehouse", "rack", "bin", "production"}
)

_ST_AVAILABLE = "available"
_ST_PENDING = "pending_inspection"
_ST_QUARANTINE = "quarantine"


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
        from_location_id: Optional[uuid.UUID] = None,
        to_location_id: Optional[uuid.UUID] = None,
    ) -> None:
        tx = InventoryTransactionModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type=transaction_type,
            quantity=float(quantity),
            unit_id=unit_id,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            reference_type=reference_type,
            reference_id=reference_id,
            remarks=remarks,
            created_by=created_by,
        )
        self._session.add(tx)

    async def _log_ledger(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        location_id: Optional[uuid.UUID],
        transaction_type: str,
        quantity_change: Decimal,
        unit_cost: Optional[float] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Append an immutable ledger row with running balance.

        Running balance = current sum of all StockLevelModel buckets for this material.
        This is called *after* bucket mutations so the balance is already updated.
        """
        running_balance = await self._sum_all_stock_levels(tenant_id, material_id)
        total_value: Optional[float] = None
        if unit_cost is not None:
            total_value = float(abs(quantity_change) * Decimal(str(unit_cost)))
        entry = StockLedgerModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=location_id,
            transaction_date=datetime.now(timezone.utc),
            transaction_type=transaction_type,
            quantity_change=float(quantity_change),
            running_balance=float(running_balance),
            unit_cost=unit_cost,
            total_value=total_value,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        self._session.add(entry)

    async def _default_warehouse_location(self, tenant_id: uuid.UUID) -> Optional[uuid.UUID]:
        stmt = (
            select(LocationModel.id)
            .where(
                LocationModel.tenant_id == tenant_id,
                LocationModel.type == "warehouse",
                LocationModel.is_deleted.is_(False),
                LocationModel.is_active.is_(True),
            )
            .limit(1)
        )
        r = await self._session.execute(stmt)
        row = r.scalar_one_or_none()
        return row

    async def _sum_available_internal(
        self, tenant_id: uuid.UUID, material_id: uuid.UUID
    ) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(StockLevelModel.quantity), 0))
            .join(LocationModel, LocationModel.id == StockLevelModel.location_id)
            .where(
                StockLevelModel.tenant_id == tenant_id,
                StockLevelModel.material_id == material_id,
                StockLevelModel.stock_status == _ST_AVAILABLE,
                StockLevelModel.is_deleted.is_(False),
                LocationModel.type.in_(_INTERNAL_ISSUE_LOCATION_TYPES),
                LocationModel.is_deleted.is_(False),
            )
        )
        r = await self._session.execute(stmt)
        return Decimal(str(r.scalar_one()))

    async def _sum_all_stock_levels(self, tenant_id: uuid.UUID, material_id: uuid.UUID) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(StockLevelModel.quantity), 0))
            .where(
                StockLevelModel.tenant_id == tenant_id,
                StockLevelModel.material_id == material_id,
                StockLevelModel.is_deleted.is_(False),
            )
        )
        r = await self._session.execute(stmt)
        return Decimal(str(r.scalar_one()))

    async def _has_stock_levels(self, tenant_id: uuid.UUID, material_id: uuid.UUID) -> bool:
        stmt = select(StockLevelModel.id).where(
            StockLevelModel.tenant_id == tenant_id,
            StockLevelModel.material_id == material_id,
            StockLevelModel.is_deleted.is_(False),
        ).limit(1)
        r = await self._session.execute(stmt)
        return r.scalar_one_or_none() is not None

    async def _sync_material_total_from_buckets(self, material: MaterialModel) -> None:
        total = await self._sum_all_stock_levels(material.tenant_id, material.id)
        material.current_stock = float(total)

    async def _lock_stock_level(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        location_id: uuid.UUID,
        stock_status: str,
    ) -> StockLevelModel:
        stmt = (
            select(StockLevelModel)
            .where(
                StockLevelModel.tenant_id == tenant_id,
                StockLevelModel.material_id == material_id,
                StockLevelModel.location_id == location_id,
                StockLevelModel.stock_status == stock_status,
                StockLevelModel.is_deleted.is_(False),
            )
            .with_for_update()
        )
        r = await self._session.execute(stmt)
        row = r.scalar_one_or_none()
        if row is None:
            row = StockLevelModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                material_id=material_id,
                location_id=location_id,
                stock_status=stock_status,
                quantity=0,
            )
            self._session.add(row)
            await self._session.flush()
            stmt2 = (
                select(StockLevelModel)
                .where(StockLevelModel.id == row.id)
                .with_for_update()
            )
            r2 = await self._session.execute(stmt2)
            row = r2.scalar_one()
        return row

    async def _deduct_available_internal(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
    ) -> Decimal:
        """Deduct from available buckets at internal locations. Returns amount still to deduct."""
        remaining = quantity
        stmt = (
            select(StockLevelModel)
            .join(LocationModel, LocationModel.id == StockLevelModel.location_id)
            .where(
                StockLevelModel.tenant_id == tenant_id,
                StockLevelModel.material_id == material_id,
                StockLevelModel.stock_status == _ST_AVAILABLE,
                StockLevelModel.is_deleted.is_(False),
                LocationModel.type.in_(_INTERNAL_ISSUE_LOCATION_TYPES),
                LocationModel.is_deleted.is_(False),
            )
            .with_for_update(of=StockLevelModel)
        )
        r = await self._session.execute(stmt)
        rows = r.scalars().all()
        for sl in rows:
            if remaining <= 0:
                break
            avail = Decimal(str(sl.quantity))
            take = min(avail, remaining)
            sl.quantity = float(avail - take)
            remaining -= take
        return remaining

    async def _add_bucket_quantity(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        location_id: uuid.UUID,
        stock_status: str,
        quantity: Decimal,
    ) -> None:
        sl = await self._lock_stock_level(tenant_id, material_id, location_id, stock_status)
        sl.quantity = float(Decimal(str(sl.quantity)) + quantity)

    async def _move_bucket_quantity(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        from_location_id: uuid.UUID,
        to_location_id: uuid.UUID,
        from_status: str,
        to_status: str,
        quantity: Decimal,
    ) -> None:
        src = await self._lock_stock_level(tenant_id, material_id, from_location_id, from_status)
        dst = await self._lock_stock_level(tenant_id, material_id, to_location_id, to_status)
        avail = Decimal(str(src.quantity))
        if quantity > avail:
            raise InsufficientStockError(
                f"Cannot move {quantity} from {from_status}: only {avail} on hand"
            )
        src.quantity = float(avail - quantity)
        dst.quantity = float(Decimal(str(dst.quantity)) + quantity)

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
        if await self._has_stock_levels(tenant_id, material_id):
            available = await self._sum_available_internal(tenant_id, material_id)
        else:
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
        """Physically issue material: decrease available stock and reserved_stock."""
        model = await self._lock_material(tenant_id, material_id)
        if await self._has_stock_levels(tenant_id, material_id):
            remaining = await self._deduct_available_internal(tenant_id, material_id, quantity)
            if remaining > 0:
                raise InsufficientStockError(
                    f"Insufficient available stock for {material_id}: "
                    f"short by {remaining} (pending inspection / quarantine not usable)"
                )
            await self._sync_material_total_from_buckets(model)
        else:
            current = Decimal(str(model.current_stock))
            if quantity > current:
                raise InsufficientStockError(
                    f"Insufficient stock for {material_id}: requested {quantity}, available {current}"
                )
            model.current_stock = float(current - quantity)
        reserved = Decimal(str(model.reserved_stock))
        model.reserved_stock = float(max(Decimal("0"), reserved - quantity))
        await self._log_transaction(
            tenant_id=tenant_id, material_id=material_id, transaction_type="issue",
            quantity=quantity, unit_id=unit_id, reference_type="work_order",
            reference_id=work_order_id, created_by=created_by,
            remarks=f"Issued for WO {work_order_id}",
        )
        # ── Stock Ledger ─────────────────────────────────────────────────────
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=None,
            transaction_type="ISSUE",
            quantity_change=-quantity,  # negative = reduction
            reference_type="work_order",
            reference_id=work_order_id,
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
        to_location_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Receive finished goods into stock after production (available at warehouse)."""
        model = await self._lock_material(tenant_id, material_id)
        loc = to_location_id or await self._default_warehouse_location(tenant_id)
        if loc:
            await self._add_bucket_quantity(
                tenant_id=tenant_id,
                material_id=material_id,
                location_id=loc,
                stock_status=_ST_AVAILABLE,
                quantity=quantity,
            )
            await self._sync_material_total_from_buckets(model)
        else:
            model.current_stock = float(Decimal(str(model.current_stock)) + quantity)
        await self._log_transaction(
            tenant_id=tenant_id, material_id=material_id, transaction_type="produce",
            quantity=quantity, unit_id=unit_id, reference_type="work_order",
            reference_id=work_order_id, created_by=created_by,
            remarks=f"Production receipt for WO {work_order_id}",
            to_location_id=loc,
        )
        # ── Stock Ledger ────────────────────────────────────────────────────
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=loc,
            transaction_type="PRODUCTION_RECEIPT",
            quantity_change=quantity,
            reference_type="work_order",
            reference_id=work_order_id,
        )

    async def receive_purchase_receipt(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        purchase_order_id: uuid.UUID,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        warehouse_location_id: Optional[uuid.UUID] = None,
        unit_cost: Optional[float] = None,
    ) -> None:
        """GRN: receipt into warehouse; pending_inspection or available based on material flag."""
        model = await self._lock_material(tenant_id, material_id)
        loc = warehouse_location_id or await self._default_warehouse_location(tenant_id)
        if loc is None:
            raise ValueError("No warehouse location configured for this tenant")
        stock_status = _ST_PENDING if getattr(model, "inspection_required", False) else _ST_AVAILABLE
        await self._add_bucket_quantity(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=loc,
            stock_status=stock_status,
            quantity=quantity,
        )
        await self._sync_material_total_from_buckets(model)
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="receipt",
            quantity=quantity,
            unit_id=unit_id,
            reference_type="purchase_order",
            reference_id=purchase_order_id,
            created_by=created_by,
            remarks="Goods receipt",
            to_location_id=loc,
        )
        # ── Stock Ledger (immutable audit) ───────────────────────────────────
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=loc,
            transaction_type="RECEIPT",
            quantity_change=quantity,
            unit_cost=unit_cost,
            reference_type="purchase_order",
            reference_id=purchase_order_id,
        )

    async def inspection_pass_move_to_available(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        warehouse_location_id: uuid.UUID,
        inspection_id: uuid.UUID,
        created_by: uuid.UUID,
    ) -> None:
        model = await self._lock_material(tenant_id, material_id)
        await self._move_bucket_quantity(
            tenant_id=tenant_id,
            material_id=material_id,
            from_location_id=warehouse_location_id,
            to_location_id=warehouse_location_id,
            from_status=_ST_PENDING,
            to_status=_ST_AVAILABLE,
            quantity=quantity,
        )
        await self._sync_material_total_from_buckets(model)
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="transfer",
            quantity=quantity,
            unit_id=model.base_unit_id,
            reference_type="quality_inspection",
            reference_id=inspection_id,
            created_by=created_by,
            remarks="Inspection pass → available",
            from_location_id=warehouse_location_id,
            to_location_id=warehouse_location_id,
        )

    async def inspection_fail_move_to_quarantine(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        warehouse_location_id: uuid.UUID,
        quarantine_location_id: uuid.UUID,
        inspection_id: uuid.UUID,
        created_by: uuid.UUID,
    ) -> None:
        model = await self._lock_material(tenant_id, material_id)
        await self._move_bucket_quantity(
            tenant_id=tenant_id,
            material_id=material_id,
            from_location_id=warehouse_location_id,
            to_location_id=quarantine_location_id,
            from_status=_ST_PENDING,
            to_status=_ST_QUARANTINE,
            quantity=quantity,
        )
        await self._sync_material_total_from_buckets(model)
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="transfer",
            quantity=quantity,
            unit_id=model.base_unit_id,
            reference_type="quality_inspection",
            reference_id=inspection_id,
            created_by=created_by,
            remarks="Inspection fail → quarantine",
            from_location_id=warehouse_location_id,
            to_location_id=quarantine_location_id,
        )

    async def issue_to_subcontractor(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        from_location_id: uuid.UUID,
        subcontractor_location_id: uuid.UUID,
        subcontract_order_id: uuid.UUID,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
    ) -> None:
        """Transfer available stock from internal warehouse to subcontractor location."""
        model = await self._lock_material(tenant_id, material_id)
        remaining = await self._deduct_available_internal(tenant_id, material_id, quantity)
        if remaining > 0:
            raise InsufficientStockError(f"Insufficient available stock for subcontract issue: {remaining} short")
        await self._add_bucket_quantity(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=subcontractor_location_id,
            stock_status=_ST_AVAILABLE,
            quantity=quantity,
        )
        await self._sync_material_total_from_buckets(model)
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="subcontract",
            quantity=quantity,
            unit_id=unit_id,
            reference_type="subcontract_order",
            reference_id=subcontract_order_id,
            created_by=created_by,
            remarks="Issue to subcontractor",
            from_location_id=from_location_id,
            to_location_id=subcontractor_location_id,
        )

    async def receive_subcontract_finished_goods(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        warehouse_location_id: uuid.UUID,
        subcontract_order_id: uuid.UUID,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
    ) -> None:
        """Receive finished goods into warehouse (available). Subcontractor WIP is tracked via issue lines."""
        model = await self._lock_material(tenant_id, material_id)
        await self._add_bucket_quantity(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=warehouse_location_id,
            stock_status=_ST_AVAILABLE,
            quantity=quantity,
        )
        await self._sync_material_total_from_buckets(model)
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="subcontract",
            quantity=quantity,
            unit_id=unit_id,
            reference_type="subcontract_order",
            reference_id=subcontract_order_id,
            created_by=created_by,
            remarks="Receive finished goods from subcontractor",
            to_location_id=warehouse_location_id,
        )
