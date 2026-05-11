"""Storekeeper Service - operational flow for storekeeper dashboard."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.manufacturing.services.inventory_service import InventoryService
from backend.app.infrastructure.persistence.models.work_order_model import (
    WorkOrderModel,
    WorkOrderMaterialModel,
)


class StorekeeperService:
    """Service for storekeeper operational dashboard and actions.

    Responsibilities:
    - Get issue queue (pending material issues)
    - Get shortage queue
    - Get partially issued WOs
    - Issue material
    - Partially issue material
    - Reject issue
    - Return material
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._inventory = InventoryService(session)

    async def get_issue_queue(self, *, tenant_id: uuid.UUID) -> list[dict]:
        """Get pending material issue queue for storekeeper dashboard."""
        # This is already implemented in InventoryService.get_pending_issues
        return await self._inventory.get_pending_issues(tenant_id=tenant_id)

    async def get_shortage_queue(self, *, tenant_id: uuid.UUID) -> list[dict]:
        """Get shortage queue for storekeeper dashboard."""
        from backend.app.infrastructure.persistence.models.material_shortage_model import MaterialShortageModel

        stmt = (
            select(MaterialShortageModel)
            .where(
                MaterialShortageModel.tenant_id == tenant_id,
                MaterialShortageModel.status.in_(["open", "partial"]),
            )
            .order_by(MaterialShortageModel.created_at)
        )
        result = await self._session.execute(stmt)
        shortages = result.scalars().all()

        shortage_queue = []
        for shortage in shortages:
            shortage_queue.append({
                "shortage_id": shortage.id,
                "work_order_id": shortage.work_order_id,
                "material_id": shortage.material_id,
                "required_quantity": shortage.required_quantity,
                "available_quantity": shortage.available_quantity,
                "shortage_quantity": shortage.shortage_quantity,
                "status": shortage.status,
                "created_at": shortage.created_at,
            })

        return shortage_queue

    async def get_partially_issued_wo(self, *, tenant_id: uuid.UUID) -> list[dict]:
        """Get partially issued WOs for storekeeper dashboard."""
        stmt = (
            select(WorkOrderModel)
            .where(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.status == "MATERIAL_ISSUED",
                WorkOrderModel.is_deleted.is_(False),
            )
            .order_by(WorkOrderModel.due_date)
        )
        result = await self._session.execute(stmt)
        wos = result.scalars().all()

        partially_issued = []
        for wo in wos:
            # Get material requirements
            mat_stmt = select(WorkOrderMaterialModel).where(
                WorkOrderMaterialModel.work_order_id == wo.id
            )
            mat_result = await self._session.execute(mat_stmt)
            materials = mat_result.scalars().all()

            # Check if any material is partially issued
            has_partial = any(
                Decimal(str(m.issued_quantity)) > 0
                and Decimal(str(m.issued_quantity)) < Decimal(str(m.required_quantity))
                for m in materials
            )

            if has_partial:
                partially_issued.append({
                    "work_order_id": wo.id,
                    "wo_number": wo.wo_number,
                    "product_id": wo.product_id,
                    "due_date": wo.due_date,
                    "status": wo.status,
                })

        return partially_issued

    async def reserve_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        reserved_by: uuid.UUID,
    ) -> None:
        """Reserve stock for work order.
        
        Triggers WO transition: MATERIAL_PENDING → MATERIAL_RESERVED.
        Inventory: AVAILABLE → RESERVED.
        """
        # Call InventoryService to reserve stock
        await self._inventory.reserve_stock(
            tenant_id=tenant_id,
            material_id=material_id,
            quantity=quantity,
            work_order_id=work_order_id,
            unit_id=unit_id,
            created_by=reserved_by,
        )
        
        # Update WO status to MATERIAL_RESERVED
        from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
        from backend.app.domain.manufacturing.entities.work_order import WorkOrderStatus
        
        stmt = select(WorkOrderModel).where(
            WorkOrderModel.id == work_order_id,
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        wo_model = result.scalar_one_or_none()
        
        if wo_model and wo_model.status == WorkOrderStatus.MATERIAL_PENDING.value:
            wo_model.status = WorkOrderStatus.MATERIAL_RESERVED.value
            wo_model.updated_at = datetime.now(timezone.utc)

    async def issue_material(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        issued_by: uuid.UUID,
    ) -> None:
        """Issue material to work order.
        
        Triggers WO transition: MATERIAL_RESERVED → MATERIAL_ISSUED.
        Inventory: RESERVED → ISSUED.
        """
        # Call InventoryService to issue stock
        await self._inventory.issue_stock(
            tenant_id=tenant_id,
            material_id=material_id,
            quantity=quantity,
            work_order_id=work_order_id,
            unit_id=unit_id,
            created_by=issued_by,
        )
        
        # Check if all materials are issued, then transition WO to MATERIAL_ISSUED
        from backend.app.infrastructure.persistence.models.work_order_model import (
            WorkOrderModel,
            WorkOrderMaterialModel,
        )
        from backend.app.domain.manufacturing.entities.work_order import WorkOrderStatus
        
        # Get WO
        stmt = select(WorkOrderModel).where(
            WorkOrderModel.id == work_order_id,
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        wo_model = result.scalar_one_or_none()
        
        if wo_model and wo_model.status == WorkOrderStatus.MATERIAL_RESERVED.value:
            # Check if all materials are fully issued
            mat_stmt = select(WorkOrderMaterialModel).where(
                WorkOrderMaterialModel.work_order_id == work_order_id
            )
            mat_result = await self._session.execute(mat_stmt)
            materials = mat_result.scalars().all()
            
            all_issued = all(
                Decimal(str(m.issued_quantity)) >= Decimal(str(m.required_quantity))
                for m in materials
            )
            
            if all_issued and materials:
                wo_model.status = WorkOrderStatus.MATERIAL_ISSUED.value
                wo_model.updated_at = datetime.now(timezone.utc)

    async def partially_issue_material(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        issued_by: uuid.UUID,
    ) -> None:
        """Partially issue material to work order."""
        await self._inventory.issue_stock(
            tenant_id=tenant_id,
            material_id=material_id,
            quantity=quantity,
            work_order_id=work_order_id,
            unit_id=unit_id,
            created_by=issued_by,
        )

    async def reject_issue(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        material_id: uuid.UUID,
        reason: str,
        rejected_by: uuid.UUID,
    ) -> None:
        """Reject material issue request.
        
        Cancels reservation and logs rejection reason.
        Inventory: RESERVED → AVAILABLE.
        """
        # Call InventoryService to cancel reservation (return stock to available)
        await self._inventory.return_stock(
            tenant_id=tenant_id,
            material_id=material_id,
            quantity=Decimal("0"),  # Will be calculated from reservation
            work_order_id=work_order_id,
            unit_id=None,
            created_by=rejected_by,
        )
        
        # Log rejection reason in audit trail
        from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderMaterialModel
        
        stmt = select(WorkOrderMaterialModel).where(
            WorkOrderMaterialModel.work_order_id == work_order_id,
            WorkOrderMaterialModel.material_id == material_id,
        )
        result = await self._session.execute(stmt)
        material_record = result.scalar_one_or_none()
        
        if material_record:
            material_record.notes = f"Rejected: {reason}"
            material_record.updated_at = datetime.now(timezone.utc)

    async def return_material(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        returned_by: uuid.UUID,
    ) -> None:
        """Return issued material back to inventory.
        
        Inventory: ISSUED → RESERVED.
        Decreases issued quantity, increases available stock.
        """
        # Call InventoryService to return stock
        await self._inventory.return_stock(
            tenant_id=tenant_id,
            material_id=material_id,
            quantity=quantity,
            work_order_id=work_order_id,
            unit_id=unit_id,
            created_by=returned_by,
        )
        
        # Update WorkOrderMaterialModel to decrease issued quantity
        from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderMaterialModel
        
        stmt = select(WorkOrderMaterialModel).where(
            WorkOrderMaterialModel.work_order_id == work_order_id,
            WorkOrderMaterialModel.material_id == material_id,
        )
        result = await self._session.execute(stmt)
        material_record = result.scalar_one_or_none()
        
        if material_record:
            current_issued = Decimal(str(material_record.issued_quantity))
            material_record.issued_quantity = max(Decimal("0"), current_issued - quantity)
            material_record.updated_at = datetime.now(timezone.utc)
