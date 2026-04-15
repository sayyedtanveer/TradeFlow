from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from backend.app.application.inventory.commands.inventory_commands import (
    MISSING,
    CreateMaterialCommand,
    UpdateMaterialCommand,
    AddStockCommand,
    RemoveStockCommand,
    AdjustStockCommand,
)
from backend.app.domain.inventory.entities.material import Material
from backend.app.domain.inventory.entities.inventory_transaction import (
    InventoryTransaction,
    TransactionType,
    ReferenceType,
)
from backend.app.infrastructure.persistence.repositories.material_repository import MaterialRepository
from backend.app.infrastructure.persistence.repositories.transaction_repository import TransactionRepository
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.infrastructure.persistence.models.inventory_management_models import StockLedgerModel
from datetime import datetime
from datetime import timezone


@dataclass
class MaterialResult:
    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    material_type: str
    description: Optional[str]
    category_id: Optional[uuid.UUID]
    base_unit_id: Optional[uuid.UUID]
    current_stock: Decimal
    reserved_stock: Decimal
    available_stock: Decimal
    reorder_level: Optional[Decimal]
    location_id: Optional[uuid.UUID]
    is_batch_tracked: bool
    is_serialized: bool
    inspection_required: bool
    inspection_template_id: Optional[uuid.UUID]
    is_active: bool
    is_low_stock: bool

def _to_result(m: Material) -> MaterialResult:
    return MaterialResult(
        id=m.id,
        tenant_id=m.tenant_id,
        code=m.code,
        name=m.name,
        material_type=m.material_type.value if hasattr(m.material_type, 'value') else m.material_type,
        description=m.description,
        category_id=m.category_id,
        base_unit_id=m.base_unit_id,
        current_stock=m.current_stock,
        reserved_stock=m.reserved_stock,
        available_stock=m.get_available_stock(),
        reorder_level=m.reorder_level,
        location_id=m.location_id,
        is_batch_tracked=m.is_batch_tracked,
        is_serialized=m.is_serialized,
        inspection_required=m.inspection_required,
        inspection_template_id=m.inspection_template_id,
        is_active=m.is_active,
        is_low_stock=m.is_low_stock(),
    )


# ── Create Material ────────────────────────────────────────────────────────
class CreateMaterialHandler:
    def __init__(self, material_repo: MaterialRepository, uow: SQLAlchemyUnitOfWork):
        self._repo = material_repo
        self._uow = uow

    async def handle(self, cmd: CreateMaterialCommand) -> MaterialResult:
        if await self._repo.code_exists(cmd.code, cmd.tenant_id):
            raise ValueError(f"Material with code '{cmd.code}' already exists in this tenant.")

        material = Material(
            tenant_id=cmd.tenant_id,
            code=cmd.code,
            name=cmd.name,
            material_type=cmd.material_type,
            description=cmd.description,
            category_id=cmd.category_id,
            base_unit_id=cmd.base_unit_id,
            reorder_level=cmd.reorder_level,
            location_id=cmd.location_id,
            is_batch_tracked=cmd.is_batch_tracked,
            is_serialized=cmd.is_serialized,
        )
        await self._repo.save(material)
        await self._uow.commit()
        return _to_result(material)


# ── Update Material ────────────────────────────────────────────────────────
class UpdateMaterialHandler:
    def __init__(self, material_repo: MaterialRepository, uow: SQLAlchemyUnitOfWork):
        self._repo = material_repo
        self._uow = uow

    async def handle(self, cmd: UpdateMaterialCommand) -> MaterialResult:
        material = await self._repo.get_by_id(cmd.id, cmd.tenant_id)
        if not material:
            raise ValueError(f"Material {cmd.id} not found.")

        material.update(
            name=cmd.name,
            description=cmd.description,
            category_id=cmd.category_id,
            base_unit_id=cmd.base_unit_id,
            material_type=cmd.material_type,
            reorder_level=cmd.reorder_level,
            location_id=cmd.location_id,
            is_batch_tracked=cmd.is_batch_tracked,
            is_serialized=cmd.is_serialized,
            is_active=cmd.is_active,
        )
        if cmd.inspection_required is not MISSING:
            material.inspection_required = cmd.inspection_required
        if cmd.inspection_template_id is not MISSING:
            material.inspection_template_id = cmd.inspection_template_id
        await self._repo.save(material)
        await self._uow.commit()
        return _to_result(material)


# ── Add Stock ──────────────────────────────────────────────────────────────
class AddStockHandler:
    def __init__(
        self,
        material_repo: MaterialRepository,
        tx_repo: TransactionRepository,
        uow: SQLAlchemyUnitOfWork,
    ):
        self._material_repo = material_repo
        self._tx_repo = tx_repo
        self._uow = uow

    async def handle(self, cmd: AddStockCommand) -> MaterialResult:
        material = await self._material_repo.get_by_id(cmd.material_id, cmd.tenant_id)
        if not material:
            raise ValueError(f"Material {cmd.material_id} not found.")
        if not material.is_active:
            raise ValueError("Cannot add stock to an inactive material.")

        material.increase_stock(cmd.quantity)

        transaction = InventoryTransaction(
            tenant_id=cmd.tenant_id,
            material_id=cmd.material_id,
            transaction_type=TransactionType.IN,
            quantity=cmd.quantity,
            unit_id=cmd.unit_id,
            to_location_id=cmd.to_location_id,
            reference_type=ReferenceType.MANUAL,
            reference_id=cmd.reference_id,
            remarks=cmd.remarks,
            created_by=cmd.created_by,
        )

        ledger_entry = StockLedgerModel(
            tenant_id=cmd.tenant_id,
            material_id=cmd.material_id,
            location_id=cmd.to_location_id,
            transaction_date=datetime.now(timezone.utc),
            transaction_type=TransactionType.IN.value,
            quantity_change=cmd.quantity,
            running_balance=material.get_available_stock(),
            reference_type=ReferenceType.MANUAL.value,
            reference_id=cmd.reference_id,
        )

        await self._material_repo.save(material)
        await self._tx_repo.save(transaction)
        self._uow.session.add(ledger_entry)
        await self._uow.commit()
        return _to_result(material)


# ── Remove Stock ───────────────────────────────────────────────────────────
class RemoveStockHandler:
    def __init__(
        self,
        material_repo: MaterialRepository,
        tx_repo: TransactionRepository,
        uow: SQLAlchemyUnitOfWork,
    ):
        self._material_repo = material_repo
        self._tx_repo = tx_repo
        self._uow = uow

    async def handle(self, cmd: RemoveStockCommand) -> MaterialResult:
        material = await self._material_repo.get_by_id(cmd.material_id, cmd.tenant_id)
        if not material:
            raise ValueError(f"Material {cmd.material_id} not found.")
        if not material.is_active:
            raise ValueError("Cannot remove stock from an inactive material.")

        # Domain rule: no negative stock — raises ValueError if insufficient
        material.decrease_stock(cmd.quantity)

        transaction = InventoryTransaction(
            tenant_id=cmd.tenant_id,
            material_id=cmd.material_id,
            transaction_type=TransactionType.OUT,
            quantity=cmd.quantity,
            unit_id=cmd.unit_id,
            from_location_id=cmd.from_location_id,
            reference_type=ReferenceType.MANUAL,
            reference_id=cmd.reference_id,
            remarks=cmd.remarks,
            created_by=cmd.created_by,
        )

        ledger_entry = StockLedgerModel(
            tenant_id=cmd.tenant_id,
            material_id=cmd.material_id,
            location_id=cmd.from_location_id,
            transaction_date=datetime.now(timezone.utc),
            transaction_type=TransactionType.OUT.value,
            quantity_change=-cmd.quantity,
            running_balance=material.get_available_stock(),
            reference_type=ReferenceType.MANUAL.value,
            reference_id=cmd.reference_id,
        )

        await self._material_repo.save(material)
        await self._tx_repo.save(transaction)
        self._uow.session.add(ledger_entry)
        await self._uow.commit()
        return _to_result(material)


# ── Adjust Stock ───────────────────────────────────────────────────────────
class AdjustStockHandler:
    def __init__(
        self,
        material_repo: MaterialRepository,
        tx_repo: TransactionRepository,
        uow: SQLAlchemyUnitOfWork,
    ):
        self._material_repo = material_repo
        self._tx_repo = tx_repo
        self._uow = uow

    async def handle(self, cmd: AdjustStockCommand) -> MaterialResult:
        material = await self._material_repo.get_by_id(cmd.material_id, cmd.tenant_id)
        if not material:
            raise ValueError(f"Material {cmd.material_id} not found.")

        delta = material.adjust_stock(cmd.new_quantity)

        # Record the absolute delta (positive = added, negative = removed)
        transaction = InventoryTransaction(
            tenant_id=cmd.tenant_id,
            material_id=cmd.material_id,
            transaction_type=TransactionType.ADJUSTMENT,
            quantity=abs(delta),
            unit_id=cmd.unit_id,
            to_location_id=cmd.location_id,  # store single location in to_location for adjustments
            from_location_id=None,
            reference_type=ReferenceType.ADJUSTMENT,
            reference_id=None,
            remarks=cmd.remarks or f"Adjusted to {cmd.new_quantity}",
            created_by=cmd.created_by,
        )

        ledger_entry = StockLedgerModel(
            tenant_id=cmd.tenant_id,
            material_id=cmd.material_id,
            location_id=cmd.location_id,
            transaction_date=datetime.now(timezone.utc),
            transaction_type=TransactionType.ADJUSTMENT.value,
            quantity_change=delta,
            running_balance=material.get_available_stock(),
            reference_type=ReferenceType.ADJUSTMENT.value,
            reference_id=None,
        )

        await self._material_repo.save(material)
        await self._tx_repo.save(transaction)
        self._uow.session.add(ledger_entry)
        await self._uow.commit()
        return _to_result(material)
