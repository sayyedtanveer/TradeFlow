"""
InventoryService â€” canonical gateway for ALL stock mutations.

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
from typing import Optional, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.batch_model import BatchModel
from backend.app.infrastructure.persistence.models.inventory_reservation_model import InventoryReservationModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
from backend.app.infrastructure.persistence.models.inventory_management_models import StockLedgerModel
from backend.app.infrastructure.persistence.models.location_model import LocationModel
from backend.app.infrastructure.persistence.models.stock_level_model import StockLevelModel
from backend.app.domain.shared.exceptions.inventory_exceptions import InsufficientStockError

# Locations usable for internal stock issue (not subcontractor / quarantine)
_INTERNAL_ISSUE_LOCATION_TYPES: frozenset[str] = frozenset(
    {"warehouse", "zone", "rack", "bin"}
)

_BLOCKED_BATCH_STATUSES: frozenset[str] = frozenset(
    {
        "EXPIRED",
        "QUARANTINED",
        "QC_HOLD",
        "PICKING_HOLD",
        "DAMAGE_HOLD",
        "INVESTIGATION_HOLD",
    }
)

_ST_AVAILABLE = "available"
_ST_PENDING = "pending_inspection"
_ST_QUARANTINE = "quarantine"


class InventoryService:
    """Single authoritative point for stock reservation, issuance, and receipt."""

    def __init__(self, session: AsyncSession):
        self._session = session

    # â”€â”€ Internal helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
        reference_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        remarks: Optional[str] = None,
        batch_id: Optional[uuid.UUID] = None,
        from_location_id: Optional[uuid.UUID] = None,
        to_location_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> InventoryTransactionModel:
        tx = InventoryTransactionModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type=transaction_type,
            quantity=float(quantity),
            unit_id=unit_id,
            batch_id=batch_id,
            warehouse_id=warehouse_id,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            reference_type=reference_type,
            reference_id=reference_id,
            remarks=remarks,
            created_by=created_by,
        )
        self._session.add(tx)
        return tx

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
        # The app-wide async session disables autoflush; flush bucket changes before
        # reading aggregate stock so material.current_stock stays authoritative.
        await self._session.flush()
        total = await self._sum_all_stock_levels(material.tenant_id, material.id)
        material.current_stock = float(total)

    async def _available_for_locked_material(self, material: MaterialModel) -> Decimal:
        """Return available stock after subtracting tenant-wide reservations."""
        if await self._has_stock_levels(material.tenant_id, material.id):
            on_hand = await self._sum_available_internal(material.tenant_id, material.id)
        else:
            on_hand = Decimal(str(material.current_stock))
        reserved = Decimal(str(material.reserved_stock))
        return max(Decimal("0"), on_hand - reserved)

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

    async def _deduct_bucket_quantity(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        location_id: uuid.UUID,
        stock_status: str,
        quantity: Decimal,
    ) -> Decimal:
        sl = await self._lock_stock_level(tenant_id, material_id, location_id, stock_status)
        available = Decimal(str(sl.quantity))
        deducted = min(available, quantity)
        sl.quantity = float(available - deducted)
        return deducted

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

    async def _lock_batch(self, tenant_id: uuid.UUID, batch_id: uuid.UUID) -> BatchModel:
        stmt = (
            select(BatchModel)
            .where(
                BatchModel.id == batch_id,
                BatchModel.tenant_id == tenant_id,
                BatchModel.is_deleted.is_(False),
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        batch = result.scalar_one_or_none()
        if batch is None:
            raise ValueError(f"Batch {batch_id} not found for tenant {tenant_id}")
        return batch

    async def _lock_batch_by_number(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        batch_number: str,
    ) -> Optional[BatchModel]:
        stmt = (
            select(BatchModel)
            .where(
                BatchModel.tenant_id == tenant_id,
                BatchModel.material_id == material_id,
                BatchModel.batch_number == batch_number,
                BatchModel.is_deleted.is_(False),
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _candidate_batches(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        batch_id: Optional[uuid.UUID] = None,
    ) -> list[BatchModel]:
        stmt = select(BatchModel).where(
            BatchModel.tenant_id == tenant_id,
            BatchModel.material_id == material_id,
            BatchModel.is_deleted.is_(False),
            func.upper(BatchModel.status).notin_(_BLOCKED_BATCH_STATUSES),
        )
        if batch_id is not None:
            stmt = stmt.where(BatchModel.id == batch_id)
        stmt = stmt.order_by(
            BatchModel.expiry_date.is_(None),
            BatchModel.expiry_date.asc(),
            BatchModel.location_id.is_(None),
            BatchModel.location_id.asc(),
            BatchModel.created_at.asc(),
            BatchModel.id.asc(),
        ).with_for_update()
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def _allocate_batch_quantities(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        batch_id: Optional[uuid.UUID] = None,
    ) -> list[tuple[BatchModel, Decimal]]:
        allocations: list[tuple[BatchModel, Decimal]] = []
        remaining = quantity
        for batch in await self._candidate_batches(
            tenant_id=tenant_id,
            material_id=material_id,
            batch_id=batch_id,
        ):
            free_qty = Decimal(str(batch.remaining_quantity if batch.remaining_quantity is not None else batch.quantity))
            free_qty -= Decimal(str(batch.reserved_quantity or 0))
            if free_qty <= 0:
                continue
            take = min(free_qty, remaining)
            allocations.append((batch, take))
            remaining -= take
            if remaining <= 0:
                break
        if remaining > 0:
            raise InsufficientStockError(
                f"Insufficient batch stock for {material_id}: short by {remaining}"
            )
        return allocations

    def _update_batch_status(self, batch: BatchModel) -> None:
        status = str(batch.status or "").upper()
        if status in _BLOCKED_BATCH_STATUSES:
            return

        remaining = Decimal(str(batch.remaining_quantity if batch.remaining_quantity is not None else batch.quantity))
        reserved = Decimal(str(batch.reserved_quantity or 0))
        consumed = Decimal(str(batch.consumed_quantity or 0))
        returned = Decimal(str(batch.returned_quantity or 0))

        if remaining <= 0:
            batch.status = "FULLY_CONSUMED"
        elif consumed > 0:
            batch.status = "PARTIALLY_CONSUMED"
        elif reserved > 0:
            batch.status = "RESERVED"
        elif returned > 0:
            batch.status = "RETURNED"
        else:
            batch.status = "AVAILABLE"
        batch.updated_at = datetime.now(timezone.utc)

    # â”€â”€ Public API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def add_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        to_location_id: Optional[uuid.UUID] = None,
        reference_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
        batch_id: Optional[uuid.UUID] = None,
        transaction_type: str = "in",
        reference_type: str = "manual",
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Canonical manual stock increase."""
        if quantity <= 0:
            raise ValueError("quantity must be positive")
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
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type=transaction_type,
            quantity=quantity,
            unit_id=unit_id,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=created_by,
            remarks=remarks,
            batch_id=batch_id,
            to_location_id=loc,
            warehouse_id=warehouse_id,
        )
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=loc,
            transaction_type=transaction_type.upper(),
            quantity_change=quantity,
            reference_type=reference_type,
            reference_id=reference_id,
        )

    async def remove_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        from_location_id: Optional[uuid.UUID] = None,
        reference_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
        batch_id: Optional[uuid.UUID] = None,
        transaction_type: str = "out",
        reference_type: str = "manual",
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Canonical manual stock decrease."""
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        model = await self._lock_material(tenant_id, material_id)

        loc = from_location_id
        if await self._has_stock_levels(tenant_id, material_id):
            if loc is not None:
                deducted = await self._deduct_bucket_quantity(
                    tenant_id=tenant_id,
                    material_id=material_id,
                    location_id=loc,
                    stock_status=_ST_AVAILABLE,
                    quantity=quantity,
                )
                remaining = quantity - deducted
            else:
                remaining = await self._deduct_available_internal(tenant_id, material_id, quantity)
            if remaining > 0:
                raise InsufficientStockError(
                    f"Insufficient available stock for {material_id}: short by {remaining}"
                )
            await self._sync_material_total_from_buckets(model)
        else:
            current = Decimal(str(model.current_stock))
            reserved = Decimal(str(model.reserved_stock))
            available = current - reserved
            if quantity > available:
                raise InsufficientStockError(
                    f"Insufficient available stock for {material_id}: requested {quantity}, available {available}"
                )
            model.current_stock = float(current - quantity)

        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type=transaction_type,
            quantity=quantity,
            unit_id=unit_id,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=created_by,
            remarks=remarks,
            batch_id=batch_id,
            from_location_id=loc,
            warehouse_id=warehouse_id,
        )
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=loc,
            transaction_type=transaction_type.upper(),
            quantity_change=-quantity,
            reference_type=reference_type,
            reference_id=reference_id,
        )

    async def adjust_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        new_quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        location_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> Decimal:
        """Canonical absolute stock adjustment. Returns signed delta."""
        if new_quantity < 0:
            raise ValueError("new_quantity cannot be negative")
        model = await self._lock_material(tenant_id, material_id)
        delta = new_quantity - Decimal(str(model.current_stock))
        if delta > 0:
            await self.add_stock(
                tenant_id=tenant_id,
                material_id=material_id,
                quantity=delta,
                unit_id=unit_id,
                created_by=created_by,
                to_location_id=location_id,
                remarks=remarks or f"Adjusted to {new_quantity}",
                transaction_type="adjustment",
                reference_type="adjustment",
                warehouse_id=warehouse_id,
            )
        elif delta < 0:
            await self.remove_stock(
                tenant_id=tenant_id,
                material_id=material_id,
                quantity=abs(delta),
                unit_id=unit_id,
                created_by=created_by,
                from_location_id=location_id,
                remarks=remarks or f"Adjusted to {new_quantity}",
                transaction_type="adjustment",
                reference_type="adjustment",
                warehouse_id=warehouse_id,
            )
        return delta

    async def add_batch_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        batch_number: str,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        expiry_date=None,
        to_location_id: Optional[uuid.UUID] = None,
        reference_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
    ) -> BatchModel:
        """Canonical batch-tracked stock increase."""
        model = await self._lock_material(tenant_id, material_id)
        if not getattr(model, "is_batch_tracked", False):
            raise ValueError(f"Material '{model.code}' is not batch-tracked")
        batch = await self._lock_batch_by_number(
            tenant_id=tenant_id,
            material_id=material_id,
            batch_number=batch_number,
        )
        loc = to_location_id or await self._default_warehouse_location(tenant_id)
        if batch is None:
            batch = BatchModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                material_id=material_id,
                batch_number=batch_number,
                quantity=float(quantity),
                original_quantity=float(quantity),
                remaining_quantity=float(quantity),
                expiry_date=expiry_date,
                location_id=loc,
                status="AVAILABLE",
            )
            self._session.add(batch)
        else:
            batch.quantity = float(Decimal(str(batch.quantity or 0)) + quantity)
            batch.original_quantity = float(
                Decimal(str(batch.original_quantity if batch.original_quantity is not None else 0)) + quantity
            )
            batch.remaining_quantity = float(
                Decimal(str(batch.remaining_quantity if batch.remaining_quantity is not None else 0)) + quantity
            )
            if expiry_date is not None:
                batch.expiry_date = expiry_date
            if loc is not None:
                batch.location_id = loc
        self._update_batch_status(batch)

        await self.add_stock(
            tenant_id=tenant_id,
            material_id=material_id,
            quantity=quantity,
            unit_id=unit_id,
            created_by=created_by,
            to_location_id=loc,
            reference_id=reference_id,
            remarks=remarks or f"Batch IN - {batch_number}",
            batch_id=batch.id,
            transaction_type="in",
            reference_type="manual",
        )
        await self._session.flush()
        return batch

    async def remove_batch_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        batch_number: str,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        from_location_id: Optional[uuid.UUID] = None,
        reference_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
    ) -> BatchModel:
        """Canonical batch-tracked stock decrease."""
        model = await self._lock_material(tenant_id, material_id)
        if not getattr(model, "is_batch_tracked", False):
            raise ValueError(f"Material '{model.code}' is not batch-tracked")
        batch = await self._lock_batch_by_number(
            tenant_id=tenant_id,
            material_id=material_id,
            batch_number=batch_number,
        )
        if batch is None:
            raise ValueError(f"Batch '{batch_number}' not found for material {material_id}")
        available = Decimal(str(batch.remaining_quantity if batch.remaining_quantity is not None else batch.quantity))
        if quantity > available:
            raise InsufficientStockError(
                f"Insufficient batch stock. Available: {available}, Requested: {quantity}"
            )
        batch.remaining_quantity = float(available - quantity)
        self._update_batch_status(batch)

        await self.remove_stock(
            tenant_id=tenant_id,
            material_id=material_id,
            quantity=quantity,
            unit_id=unit_id,
            created_by=created_by,
            from_location_id=from_location_id or batch.location_id,
            reference_id=reference_id,
            remarks=remarks or f"Batch OUT - {batch_number}",
            batch_id=batch.id,
            transaction_type="out",
            reference_type="manual",
        )
        await self._session.flush()
        return batch

    async def reserve_reference_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
    ) -> None:
        """Reserve stock for a legacy non-WO reference without creating a WO reservation row."""
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        model = await self._lock_material(tenant_id, material_id)
        current = Decimal(str(model.current_stock or 0))
        reserved = Decimal(str(model.reserved_stock or 0))
        available = current - reserved
        if quantity > available:
            raise InsufficientStockError(
                f"Insufficient stock for {material_id}: requested {quantity}, available {available}"
            )
        model.reserved_stock = float(reserved + quantity)
        model.updated_at = datetime.now(timezone.utc)
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="reserve",
            quantity=quantity,
            unit_id=unit_id,
            reference_type=reference_type or "manual",
            reference_id=reference_id,
            created_by=created_by,
            remarks=remarks or "Legacy stock reservation",
        )

    async def consume_reference_reservation(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        from_location_id: Optional[uuid.UUID] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
    ) -> None:
        """Consume a legacy reservation through the canonical mutation path."""
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        model = await self._lock_material(tenant_id, material_id)
        if await self._has_stock_levels(tenant_id, material_id):
            remaining = quantity
            if from_location_id is not None:
                deducted = await self._deduct_bucket_quantity(
                    tenant_id=tenant_id,
                    material_id=material_id,
                    location_id=from_location_id,
                    stock_status=_ST_AVAILABLE,
                    quantity=quantity,
                )
                remaining -= deducted
            if remaining > 0:
                remaining = await self._deduct_available_internal(tenant_id, material_id, remaining)
            if remaining > 0:
                raise InsufficientStockError(
                    f"Insufficient available stock for {material_id}: short by {remaining}"
                )
            await self._sync_material_total_from_buckets(model)
        else:
            current = Decimal(str(model.current_stock or 0))
            if quantity > current:
                raise InsufficientStockError(
                    f"Insufficient stock for {material_id}: requested {quantity}, available {current}"
                )
            model.current_stock = float(current - quantity)

        reserved = Decimal(str(model.reserved_stock or 0))
        model.reserved_stock = float(max(Decimal("0"), reserved - quantity))
        model.updated_at = datetime.now(timezone.utc)
        ref_type = reference_type or "manual"
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="consume_reservation",
            quantity=quantity,
            unit_id=unit_id,
            reference_type=ref_type,
            reference_id=reference_id,
            created_by=created_by,
            remarks=remarks or "Legacy reservation consumed",
            from_location_id=from_location_id,
        )
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=from_location_id,
            transaction_type="CONSUME_RESERVATION",
            quantity_change=-quantity,
            reference_type=ref_type,
            reference_id=reference_id,
        )

    async def cancel_reference_reservation(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
    ) -> None:
        """Release a legacy reservation through the canonical mutation path."""
        if quantity <= 0:
            return
        model = await self._lock_material(tenant_id, material_id)
        reserved = Decimal(str(model.reserved_stock or 0))
        model.reserved_stock = float(max(Decimal("0"), reserved - quantity))
        model.updated_at = datetime.now(timezone.utc)
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="reservation_cancel",
            quantity=quantity,
            unit_id=unit_id,
            reference_type=reference_type or "manual",
            reference_id=reference_id,
            created_by=created_by,
            remarks=remarks or "Legacy reservation cancelled",
        )

    async def get_available_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
    ) -> Decimal:
        """Read available, unreserved stock for a material."""
        model = await self._lock_material(tenant_id, material_id)
        return await self._available_for_locked_material(model)

    async def get_available_stock_for_warehouse(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        warehouse_id: uuid.UUID,
    ) -> Decimal:
        """Get available stock for a material within a specific warehouse.

        Available = warehouse_stock - warehouse_reserved.
        Uses stock_levels filtered by warehouse_id and subtracts active
        reservations scoped to that warehouse.

        This implements the requirement: available_quantity = current_stock - reserved_quantity
        at the warehouse level for accurate per-warehouse inventory validation.
        """
        # Get warehouse-scoped on-hand stock
        stmt = (
            select(func.coalesce(func.sum(StockLevelModel.quantity), 0))
            .where(
                StockLevelModel.tenant_id == tenant_id,
                StockLevelModel.material_id == material_id,
                StockLevelModel.warehouse_id == warehouse_id,
                StockLevelModel.stock_status == _ST_AVAILABLE,
                StockLevelModel.is_deleted.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        on_hand = Decimal(str(result.scalar_one()))

        # Get warehouse-scoped reserved quantity from reservation records
        reserved_stmt = (
            select(func.coalesce(func.sum(InventoryReservationModel.quantity), 0))
            .where(
                InventoryReservationModel.tenant_id == tenant_id,
                InventoryReservationModel.material_id == material_id,
                InventoryReservationModel.warehouse_id == warehouse_id,
                InventoryReservationModel.status == "RESERVED",
            )
        )
        reserved_result = await self._session.execute(reserved_stmt)
        reserved = Decimal(str(reserved_result.scalar_one()))

        return max(Decimal("0"), on_hand - reserved)

    async def get_total_reserved_for_material(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
    ) -> Decimal:
        """Get total reserved quantity across all warehouses for a material."""
        stmt = (
            select(func.coalesce(func.sum(InventoryReservationModel.quantity), 0))
            .where(
                InventoryReservationModel.tenant_id == tenant_id,
                InventoryReservationModel.material_id == material_id,
                InventoryReservationModel.status == "RESERVED",
            )
        )
        result = await self._session.execute(stmt)
        return Decimal(str(result.scalar_one()))

    async def release_all_reservations_for_order(
        self,
        *,
        tenant_id: uuid.UUID,
        order_id: uuid.UUID,
        created_by: uuid.UUID,
    ) -> None:
        """Release all active reservations for an order (on cancellation).

        Finds all RESERVED reservation records for the given order_id,
        marks them as RELEASED, and decrements each material's reserved_stock.

        Requirements: 6.3 (inventory insufficient → cancel → release),
                      6.13 (admin cancel → release reserved inventory)
        """
        stmt = (
            select(InventoryReservationModel)
            .where(
                InventoryReservationModel.tenant_id == tenant_id,
                InventoryReservationModel.order_id == order_id,
                InventoryReservationModel.status == "RESERVED",
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        reservations = result.scalars().all()

        for reservation in reservations:
            quantity = Decimal(str(reservation.quantity))
            reservation.status = "RELEASED"

            # Decrement material's reserved_stock
            material = await self._lock_material(tenant_id, reservation.material_id)
            current_reserved = Decimal(str(material.reserved_stock))
            material.reserved_stock = float(max(Decimal("0"), current_reserved - quantity))

            await self._log_transaction(
                tenant_id=tenant_id,
                material_id=reservation.material_id,
                transaction_type="release",
                quantity=quantity,
                unit_id=reservation.unit_id,
                reference_type="sales_order_line",
                reference_id=reservation.reference_id,
                created_by=created_by,
                remarks=f"Released reservation for cancelled order {order_id}",
                warehouse_id=reservation.warehouse_id,
            )

    async def reserve_sales_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        sales_order_line_id: uuid.UUID,
        unit_id: Optional[uuid.UUID] = None,
        created_by: uuid.UUID,
        warehouse_id: Optional[uuid.UUID] = None,
        order_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Reserve finished goods for a sales order line without reducing on-hand stock.

        Creates an InventoryReservationModel record for audit and tracking,
        and increments the material's reserved_stock counter to reflect the
        available quantity calculation: current_stock - reserved_quantity.

        Requirements: 5.7 (reserve on order confirmation to prevent overselling)
        """
        model = await self._lock_material(tenant_id, material_id)
        available = await self._available_for_locked_material(model)
        if quantity > available:
            raise InsufficientStockError(
                f"Cannot reserve {quantity}: only {available} available for {material_id}"
            )
        model.reserved_stock = float(Decimal(str(model.reserved_stock)) + quantity)

        # Create reservation record for audit trail and lifecycle tracking
        reservation = InventoryReservationModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            reference_type="sales_order_line",
            reference_id=sales_order_line_id,
            material_id=material_id,
            quantity=float(quantity),
            status="RESERVED",
            unit_id=unit_id,
            warehouse_id=warehouse_id,
            order_id=order_id,
            issued_quantity=0,
            consumed_quantity=0,
            returned_quantity=0,
        )
        self._session.add(reservation)

        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="reserve",
            quantity=quantity,
            unit_id=unit_id,
            reference_type="sales_order_line",
            reference_id=sales_order_line_id,
            created_by=created_by,
            remarks=f"Reserved for sales order line {sales_order_line_id}",
            warehouse_id=warehouse_id,
        )

    async def release_sales_reservation(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        sales_order_line_id: uuid.UUID,
        unit_id: Optional[uuid.UUID] = None,
        created_by: uuid.UUID,
    ) -> None:
        """Release a sales reservation back to available stock.

        Updates the InventoryReservationModel record to RELEASED status and
        decrements the material's reserved_stock counter.

        Requirements: 6.3 (release on cancellation), 6.13 (release on admin cancel)
        """
        model = await self._lock_material(tenant_id, material_id)
        reserved = Decimal(str(model.reserved_stock))
        released = min(quantity, reserved)
        model.reserved_stock = float(reserved - released)

        # Update reservation record status to RELEASED
        if released > 0:
            stmt = (
                select(InventoryReservationModel)
                .where(
                    InventoryReservationModel.tenant_id == tenant_id,
                    InventoryReservationModel.reference_type == "sales_order_line",
                    InventoryReservationModel.reference_id == sales_order_line_id,
                    InventoryReservationModel.material_id == material_id,
                    InventoryReservationModel.status == "RESERVED",
                )
                .with_for_update()
            )
            result = await self._session.execute(stmt)
            reservation_row = result.scalar_one_or_none()
            if reservation_row is not None:
                reservation_row.status = "RELEASED"

            await self._log_transaction(
                tenant_id=tenant_id,
                material_id=material_id,
                transaction_type="release",
                quantity=released,
                unit_id=unit_id,
                reference_type="sales_order_line",
                reference_id=sales_order_line_id,
                created_by=created_by,
                remarks=f"Released reservation for sales order line {sales_order_line_id}",
            )

    async def fulfill_sales_reservation(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        sales_order_line_id: uuid.UUID,
        unit_id: Optional[uuid.UUID] = None,
        created_by: uuid.UUID,
    ) -> None:
        """Ship reserved goods: deduct physical stock and consume the reservation.

        Updates the InventoryReservationModel record to CONSUMED status
        after deducting physical stock.
        """
        model = await self._lock_material(tenant_id, material_id)
        if await self._has_stock_levels(tenant_id, material_id):
            remaining = await self._deduct_available_internal(tenant_id, material_id, quantity)
            if remaining > 0:
                raise InsufficientStockError(
                    f"Insufficient available stock for {material_id}: short by {remaining}"
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

        # Update reservation record status to CONSUMED
        stmt = (
            select(InventoryReservationModel)
            .where(
                InventoryReservationModel.tenant_id == tenant_id,
                InventoryReservationModel.reference_type == "sales_order_line",
                InventoryReservationModel.reference_id == sales_order_line_id,
                InventoryReservationModel.material_id == material_id,
                InventoryReservationModel.status == "RESERVED",
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        reservation_row = result.scalar_one_or_none()
        if reservation_row is not None:
            reservation_row.status = "CONSUMED"
            reservation_row.consumed_quantity = float(
                Decimal(str(reservation_row.consumed_quantity or 0)) + quantity
            )

        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="issue",
            quantity=quantity,
            unit_id=unit_id,
            reference_type="sales_order_line",
            reference_id=sales_order_line_id,
            created_by=created_by,
            remarks=f"Shipped for sales order line {sales_order_line_id}",
        )
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=None,
            transaction_type="SALES_SHIPMENT",
            quantity_change=-quantity,
            reference_type="sales_order_line",
            reference_id=sales_order_line_id,
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
            reference_type="purchase_receipt",
            reference_id=purchase_order_id,
            created_by=created_by,
            remarks="Goods receipt",
            to_location_id=loc,
        )
        # â”€â”€ Stock Ledger (immutable audit) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    async def reverse_purchase_receipt(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        purchase_order_id: uuid.UUID,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        warehouse_location_id: Optional[uuid.UUID] = None,
        reference_type: str = "purchase_receipt_reversal",
        reference_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
    ) -> None:
        """Reverse a previously received purchase quantity through the canonical stock service."""
        model = await self._lock_material(tenant_id, material_id)
        loc = warehouse_location_id or await self._default_warehouse_location(tenant_id)

        if await self._has_stock_levels(tenant_id, material_id):
            if loc is None:
                raise ValueError("No warehouse location configured for this tenant")

            remaining = quantity
            preferred_statuses = [_ST_PENDING] if getattr(model, "inspection_required", False) else []
            preferred_statuses.extend([_ST_AVAILABLE, _ST_PENDING])

            for stock_status in preferred_statuses:
                if remaining <= 0:
                    break
                deducted = await self._deduct_bucket_quantity(
                    tenant_id=tenant_id,
                    material_id=material_id,
                    location_id=loc,
                    stock_status=stock_status,
                    quantity=remaining,
                )
                remaining -= deducted

            if remaining > 0:
                remaining = await self._deduct_available_internal(tenant_id, material_id, remaining)
            if remaining > 0:
                raise InsufficientStockError(
                    f"Cannot reverse receipt {quantity}: only {quantity - remaining} is still available"
                )

            await self._sync_material_total_from_buckets(model)
        else:
            current = Decimal(str(model.current_stock))
            if quantity > current:
                raise InsufficientStockError(
                    f"Cannot reverse receipt {quantity}: only {current} remains in stock"
                )
            model.current_stock = float(current - quantity)

        reversal_reference_id = reference_id or purchase_order_id
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="reverse_receipt",
            quantity=quantity,
            unit_id=unit_id,
            reference_type=reference_type,
            reference_id=reversal_reference_id,
            created_by=created_by,
            remarks=remarks or "Goods receipt reversal",
            from_location_id=loc,
        )
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=loc,
            transaction_type="RECEIPT_REVERSAL",
            quantity_change=-quantity,
            reference_type=reference_type,
            reference_id=reversal_reference_id,
        )

    async def transfer_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        from_location_id: uuid.UUID,
        to_location_id: uuid.UUID,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        reference_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
    ) -> None:
        """Transfer available stock between two locations for the same material."""
        if from_location_id == to_location_id:
            raise ValueError("from_location_id and to_location_id must be different for a transfer")

        model = await self._lock_material(tenant_id, material_id)
        if not await self._has_stock_levels(tenant_id, material_id):
            current = Decimal(str(model.current_stock))
            if quantity > current:
                raise InsufficientStockError(
                    f"Cannot transfer {quantity}: only {current} available for {material_id}"
                )
            await self._add_bucket_quantity(
                tenant_id=tenant_id,
                material_id=material_id,
                location_id=from_location_id,
                stock_status=_ST_AVAILABLE,
                quantity=current,
            )
            await self._session.flush()
        await self._move_bucket_quantity(
            tenant_id=tenant_id,
            material_id=material_id,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            from_status=_ST_AVAILABLE,
            to_status=_ST_AVAILABLE,
            quantity=quantity,
        )
        await self._sync_material_total_from_buckets(model)

        transfer_reference_id = reference_id or uuid.uuid4()
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="transfer",
            quantity=quantity,
            unit_id=unit_id,
            reference_type="inventory_transfer",
            reference_id=transfer_reference_id,
            created_by=created_by,
            remarks=remarks or "Inventory transfer",
            from_location_id=from_location_id,
            to_location_id=to_location_id,
        )
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=to_location_id,
            transaction_type="TRANSFER",
            quantity_change=Decimal("0"),
            reference_type="inventory_transfer",
            reference_id=transfer_reference_id,
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
            unit_id=cast(Optional[uuid.UUID], model.base_unit_id),
            reference_type="quality_inspection",
            reference_id=inspection_id,
            created_by=created_by,
            remarks="Inspection pass â†’ available",
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
            unit_id=cast(Optional[uuid.UUID], model.base_unit_id),
            reference_type="quality_inspection",
            reference_id=inspection_id,
            created_by=created_by,
            remarks="Inspection fail â†’ quarantine",
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

