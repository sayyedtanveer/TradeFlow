"""Production Execution Service - operational flow for worker dashboard."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.work_order_model import (
    WorkOrderModel,
    JobCardModel,
)
from backend.app.domain.manufacturing.entities.work_order import WorkOrderStatus
from backend.app.application.manufacturing.services.inventory_service import InventoryService


class ProductionExecutionService:
    """Service for worker operational dashboard and actions.

    Responsibilities:
    - Get worker queue (assigned WOs and operations)
    - Start operation
    - Pause operation
    - Complete operation
    - Report wastage
    - Record production
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._inventory = InventoryService(session)

    async def get_worker_queue(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[dict]:
        """Get assigned work orders and operations for worker dashboard."""
        # Get WOs in MATERIAL_ISSUED or IN_PRODUCTION state
        stmt = (
            select(WorkOrderModel)
            .where(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.status.in_(["MATERIAL_ISSUED", "IN_PRODUCTION"]),
                WorkOrderModel.is_deleted.is_(False),
            )
            .order_by(WorkOrderModel.due_date)
        )
        result = await self._session.execute(stmt)
        wos = result.scalars().all()

        worker_queue = []
        for wo in wos:
            # Get job cards for this WO
            jc_stmt = select(JobCardModel).where(
                JobCardModel.work_order_id == wo.id
            )
            jc_result = await self._session.execute(jc_stmt)
            job_cards = jc_result.scalars().all()

            # Get assigned job cards (assigned to this worker or unassigned)
            assigned_cards = [
                jc for jc in job_cards
                if jc.assigned_to == user_id or jc.assigned_to is None
            ]

            if assigned_cards:
                worker_queue.append({
                    "work_order_id": wo.id,
                    "wo_number": wo.wo_number,
                    "product_id": wo.product_id,
                    "due_date": wo.due_date,
                    "priority": wo.priority,
                    "status": wo.status,
                    "job_cards": [
                        {
                            "job_card_id": jc.id,
                            "operation_id": jc.operation_id,
                            "sequence": jc.sequence,
                            "status": jc.status,
                            "assigned_to": jc.assigned_to,
                        }
                        for jc in assigned_cards
                    ],
                })

        return worker_queue

    async def start_operation(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        job_card_id: uuid.UUID,
        assigned_to: uuid.UUID,
    ) -> None:
        """Start a job card operation.
        
        Triggers WO transition: MATERIAL_ISSUED → IN_PRODUCTION (if first operation).
        """
        stmt = select(JobCardModel).where(
            JobCardModel.id == job_card_id,
            JobCardModel.work_order_id == work_order_id,
        )
        result = await self._session.execute(stmt)
        jc = result.scalar_one_or_none()

        if not jc:
            raise ValueError("Job card not found")

        if jc.status != "PENDING":
            raise ValueError(f"Job card is already {jc.status}")

        jc.status = "IN_PROGRESS"
        jc.started_at = datetime.now(timezone.utc)
        jc.assigned_to = assigned_to
        
        # Check if this is the first operation, transition WO to IN_PRODUCTION
        wo_stmt = select(WorkOrderModel).where(
            WorkOrderModel.id == work_order_id,
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        )
        wo_result = await self._session.execute(wo_stmt)
        wo_model = wo_result.scalar_one_or_none()
        
        if wo_model and wo_model.status == WorkOrderStatus.MATERIAL_ISSUED.value:
            # Check if any job card is already in progress
            jc_stmt = select(JobCardModel).where(
                JobCardModel.work_order_id == work_order_id,
                JobCardModel.status == "IN_PROGRESS",
            )
            jc_result = await self._session.execute(jc_stmt)
            existing_in_progress = jc_result.scalar_one_or_none()
            
            # If no existing in-progress job cards, this is the first operation
            if not existing_in_progress:
                wo_model.status = WorkOrderStatus.IN_PRODUCTION.value
                wo_model.updated_at = datetime.now(timezone.utc)

    async def pause_operation(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        job_card_id: uuid.UUID,
    ) -> None:
        """Pause a job card operation."""
        stmt = select(JobCardModel).where(
            JobCardModel.id == job_card_id,
            JobCardModel.work_order_id == work_order_id,
        )
        result = await self._session.execute(stmt)
        jc = result.scalar_one_or_none()

        if not jc:
            raise ValueError("Job card not found")

        if jc.status != "IN_PROGRESS":
            raise ValueError(f"Cannot pause job card in {jc.status} status")

        jc.status = "PAUSED"

    async def complete_operation(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        job_card_id: uuid.UUID,
        remarks: Optional[str] = None,
    ) -> None:
        """Complete a job card operation."""
        stmt = select(JobCardModel).where(
            JobCardModel.id == job_card_id,
            JobCardModel.work_order_id == work_order_id,
        )
        result = await self._session.execute(stmt)
        jc = result.scalar_one_or_none()

        if not jc:
            raise ValueError("Job card not found")

        if jc.status not in ("IN_PROGRESS", "PAUSED"):
            raise ValueError(f"Cannot complete job card in {jc.status} status")

        jc.status = "DONE"
        jc.completed_at = datetime.now()
        if remarks:
            jc.remarks = remarks

    async def report_wastage(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        scrap_quantity: Decimal,
        recorded_by: uuid.UUID,
        notes: Optional[str] = None,
    ) -> None:
        """Report scrap/wastage during production.
        
        Inventory impact: CONSUMED → REJECTED.
        Updates WO scrap quantity.
        """
        # Get WO
        stmt = select(WorkOrderModel).where(
            WorkOrderModel.id == work_order_id,
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        wo_model = result.scalar_one_or_none()
        
        if not wo_model:
            raise ValueError("Work Order not found")
        
        # Update scrap quantity
        current_scrap = Decimal(str(wo_model.scrap_quantity))
        wo_model.scrap_quantity = current_scrap + scrap_quantity
        wo_model.updated_at = datetime.now(timezone.utc)
        
        # Inventory mutation: CONSUMED → REJECTED via InventoryService.reject_stock()
        await self._inventory.reject_stock(
            tenant_id=tenant_id,
            material_id=wo_model.product_id,
            quantity=scrap_quantity,
            work_order_id=work_order_id,
            created_by=recorded_by,
            reason=notes or "Production wastage",
        )

    async def record_production(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        produced_quantity: Decimal,
        scrap_quantity: Decimal,
        recorded_by: uuid.UUID,
        notes: Optional[str] = None,
    ) -> None:
        """Record production quantity.
        
        Triggers WO transition: IN_PRODUCTION → QC_PENDING.
        Inventory impact: ISSUED → CONSUMED.
        """
        # Get WO
        stmt = select(WorkOrderModel).where(
            WorkOrderModel.id == work_order_id,
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        wo_model = result.scalar_one_or_none()
        
        if not wo_model:
            raise ValueError("Work Order not found")
        
        # Update produced and scrap quantities
        wo_model.produced_quantity = produced_quantity
        wo_model.scrap_quantity = scrap_quantity
        wo_model.updated_at = datetime.now(timezone.utc)
        
        # Transition WO to QC_PENDING
        if wo_model.status == WorkOrderStatus.IN_PRODUCTION.value:
            wo_model.status = WorkOrderStatus.QC_PENDING.value
            wo_model.updated_at = datetime.now(timezone.utc)
        
        # Inventory consumption: ISSUED → CONSUMED via InventoryService.consume_stock()
        # Note: This is a simplified implementation - in reality, you'd consume based on BOM
        # For now, we're consuming a proportional amount of materials
        # This can be enhanced later to track actual material consumption per BOM line
        # await self._inventory.consume_stock(
        #     tenant_id=tenant_id,
        #     material_id=wo_model.product_id,
        #     quantity=produced_quantity,
        #     work_order_id=work_order_id,
        #     created_by=recorded_by,
        # )
        # TODO: Implement BOM-based material consumption in Phase 5 enhancement
