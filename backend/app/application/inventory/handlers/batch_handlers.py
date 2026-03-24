from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from backend.app.application.inventory.commands.inventory_commands import (
    AddStockWithBatchCommand,
    RemoveStockFromBatchCommand,
)
from backend.app.application.inventory.queries.inventory_queries import (
    GetBatchesByMaterialQuery,
    GetExpiringBatchesQuery,
)
from backend.app.domain.inventory.entities.batch import Batch
from backend.app.domain.inventory.entities.inventory_transaction import (
    InventoryTransaction,
    ReferenceType,
    TransactionType,
)
from backend.app.infrastructure.persistence.repositories.batch_repository import BatchRepository
from backend.app.infrastructure.persistence.repositories.material_repository import MaterialRepository
from backend.app.infrastructure.persistence.repositories.transaction_repository import TransactionRepository
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork


# ── Result DTOs ────────────────────────────────────────────────────────────────

@dataclass
class BatchResult:
    id: uuid.UUID
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    batch_number: str
    quantity: Decimal
    remaining_quantity: Decimal
    expiry_date: Optional[date]
    location_id: Optional[uuid.UUID]
    status: str
    is_expired: bool
    days_until_expiry: Optional[int]
    created_at: str


def _to_batch_result(batch: Batch) -> BatchResult:
    return BatchResult(
        id=batch.id,
        tenant_id=batch.tenant_id,
        material_id=batch.material_id,
        batch_number=batch.batch_number,
        quantity=batch.quantity,
        remaining_quantity=batch.remaining_quantity,
        expiry_date=batch.expiry_date,
        location_id=batch.location_id,
        status=batch.status.value,
        is_expired=batch.is_expired(),
        days_until_expiry=batch.days_until_expiry(),
        created_at=batch.created_at.isoformat(),
    )


# ── Add Stock With Batch ───────────────────────────────────────────────────────

class AddStockWithBatchHandler:
    """
    Adds stock to a batch-tracked material.
    - If the batch_number already exists, its quantity is increased.
    - If it's new, a fresh Batch record is created.
    - Always updates Material.current_stock and records a transaction.
    """

    def __init__(
        self,
        material_repo: MaterialRepository,
        batch_repo: BatchRepository,
        tx_repo: TransactionRepository,
        uow: SQLAlchemyUnitOfWork,
    ) -> None:
        self._material_repo = material_repo
        self._batch_repo = batch_repo
        self._tx_repo = tx_repo
        self._uow = uow

    async def handle(self, cmd: AddStockWithBatchCommand) -> BatchResult:
        # 1. Load & validate material
        material = await self._material_repo.get_by_id(cmd.material_id, cmd.tenant_id)
        if not material:
            raise ValueError(f"Material {cmd.material_id} not found.")
        if not material.is_active:
            raise ValueError("Cannot add stock to an inactive material.")
        if not material.is_batch_tracked:
            raise ValueError(
                f"Material '{material.code}' is not batch-tracked. "
                "Set is_batch_tracked=true before using batch stock operations."
            )

        # 2. Load or create batch
        batch = await self._batch_repo.get_by_batch_number(
            cmd.batch_number, cmd.material_id, cmd.tenant_id
        )
        if batch is None:
            batch = Batch(
                tenant_id=cmd.tenant_id,
                material_id=cmd.material_id,
                batch_number=cmd.batch_number,
                quantity=Decimal("0"),
                expiry_date=cmd.expiry_date,
            )
        batch.increase_quantity(cmd.quantity)

        # 3. Update aggregate material stock
        material.increase_stock(cmd.quantity)

        # 4. Record transaction
        tx = InventoryTransaction(
            tenant_id=cmd.tenant_id,
            material_id=cmd.material_id,
            transaction_type=TransactionType.IN,
            quantity=cmd.quantity,
            unit_id=cmd.unit_id,
            to_location_id=cmd.to_location_id,
            reference_type=ReferenceType.MANUAL,
            reference_id=cmd.reference_id,
            remarks=cmd.remarks or f"Batch IN — {cmd.batch_number}",
            created_by=cmd.created_by,
        )

        await self._batch_repo.save(batch)
        await self._material_repo.save(material)
        await self._tx_repo.save(tx)
        await self._uow.commit()
        return _to_batch_result(batch)


# ── Remove Stock From Batch ────────────────────────────────────────────────────

class RemoveStockFromBatchHandler:
    """
    Removes stock from a specific batch.
    - Enforces no-negative at batch level.
    - Updates Material.current_stock.
    - Records transaction.
    """

    def __init__(
        self,
        material_repo: MaterialRepository,
        batch_repo: BatchRepository,
        tx_repo: TransactionRepository,
        uow: SQLAlchemyUnitOfWork,
    ) -> None:
        self._material_repo = material_repo
        self._batch_repo = batch_repo
        self._tx_repo = tx_repo
        self._uow = uow

    async def handle(self, cmd: RemoveStockFromBatchCommand) -> BatchResult:
        material = await self._material_repo.get_by_id(cmd.material_id, cmd.tenant_id)
        if not material:
            raise ValueError(f"Material {cmd.material_id} not found.")
        if not material.is_active:
            raise ValueError("Cannot remove stock from an inactive material.")

        batch = await self._batch_repo.get_by_batch_number(
            cmd.batch_number, cmd.material_id, cmd.tenant_id
        )
        if not batch:
            raise ValueError(
                f"Batch '{cmd.batch_number}' not found for material {cmd.material_id}."
            )

        # Domain rule enforced inside Batch entity
        batch.decrease_quantity(cmd.quantity)
        material.decrease_stock(cmd.quantity)

        tx = InventoryTransaction(
            tenant_id=cmd.tenant_id,
            material_id=cmd.material_id,
            transaction_type=TransactionType.OUT,
            quantity=cmd.quantity,
            unit_id=cmd.unit_id,
            from_location_id=cmd.from_location_id,
            reference_type=ReferenceType.MANUAL,
            reference_id=cmd.reference_id,
            remarks=cmd.remarks or f"Batch OUT — {cmd.batch_number}",
            created_by=cmd.created_by,
        )

        await self._batch_repo.save(batch)
        await self._material_repo.save(material)
        await self._tx_repo.save(tx)
        await self._uow.commit()
        return _to_batch_result(batch)


# ── Batch Query Handler ────────────────────────────────────────────────────────

class BatchQueryHandler:
    def __init__(self, batch_repo: BatchRepository) -> None:
        self._batch_repo = batch_repo

    async def get_batches_by_material(
        self, query: GetBatchesByMaterialQuery
    ) -> List[BatchResult]:
        batches = await self._batch_repo.list_by_material(
            material_id=query.material_id,
            tenant_id=query.tenant_id,
        )
        return [_to_batch_result(b) for b in batches]

    async def get_expiring_batches(
        self, query: GetExpiringBatchesQuery
    ) -> List[BatchResult]:
        from datetime import date, timedelta
        before_date = date.today() + timedelta(days=query.days_ahead)
        batches = await self._batch_repo.list_expiring(
            tenant_id=query.tenant_id,
            before_date=before_date,
        )
        return [_to_batch_result(b) for b in batches]
