"""
WorkOrderHandler — orchestrates all Work Order use cases.

Data flow: API → Command → Handler → Domain Entity + Services → Repository → DB
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.application.manufacturing.commands.work_order_commands import (
    CreateWorkOrderCommand, ReleaseWorkOrderCommand, StartWorkOrderCommand,
    IssueMaterialCommand, RecordProductionCommand,
    CompleteWorkOrderCommand, CloseWorkOrderCommand,
    StartJobCardCommand, CompleteJobCardCommand,
)
from backend.app.application.manufacturing.services.inventory_service import InventoryService
from backend.app.application.manufacturing.services.wo_number_service import WONumberService
from backend.app.domain.manufacturing.entities.work_order import WorkOrder, WorkOrderStatus, WorkOrderPriority
from backend.app.domain.manufacturing.exceptions import BOMNotFoundError, MaterialNotIssuedError
from backend.app.domain.manufacturing.events.work_order_events import (
    WorkOrderReleased, WorkOrderStarted, WorkOrderCompleted, WorkOrderClosed,
)
from backend.app.infrastructure.persistence.models.work_order_model import (
    WorkOrderModel, WorkOrderMaterialModel, JobCardModel, ProductionRecordModel
)
from backend.app.infrastructure.persistence.models.bom_model import BOMModel, BOMLineModel
from backend.app.infrastructure.persistence.models.bom_operation_model import BOMOperationModel


class WorkOrderHandler:
    def __init__(self, session: AsyncSession, uow=None):
        self._session = session
        self._uow = uow  # Optional: UnitOfWork for emitting domain events
        self._inventory = InventoryService(session)
        self._wo_number = WONumberService(session)

    def with_uow(self, uow):
        """Fluent setter for UnitOfWork (for event emission)."""
        self._uow = uow
        return self

    def _emit_event(self, event) -> None:
        """Emit a domain event via UnitOfWork if available."""
        if self._uow is not None:
            self._uow.register_events([event])

    # ── Create ──────────────────────────────────────────────────────────────────

    async def handle_create(self, cmd: CreateWorkOrderCommand) -> uuid.UUID:
        # 1. Load BOM with lines + operations
        bom_stmt = (
            select(BOMModel)
            .options(selectinload(BOMModel.lines), selectinload(BOMModel.operations))
            .where(BOMModel.id == cmd.bom_id, BOMModel.tenant_id == cmd.tenant_id, BOMModel.is_deleted.is_(False))
        )
        result = await self._session.execute(bom_stmt)
        bom = result.scalar_one_or_none()
        if not bom:
            raise BOMNotFoundError(f"BOM {cmd.bom_id} not found or inactive")

        # 2. Generate WO number (atomic)
        wo_number = await self._wo_number.generate(cmd.tenant_id)

        # 3. Create WO model
        wo = WorkOrderModel(
            id=uuid.uuid4(),
            wo_number=wo_number,
            tenant_id=cmd.tenant_id,
            product_id=cmd.product_id,
            bom_id=cmd.bom_id,
            planned_quantity=float(cmd.planned_quantity),
            produced_quantity=0,
            scrap_quantity=0,
            status=WorkOrderStatus.PLANNED,
            priority=WorkOrderPriority[cmd.priority],
            start_date=cmd.start_date,
            due_date=cmd.due_date,
            sales_order_id=cmd.sales_order_id,
            notes=cmd.notes,
            created_by=cmd.created_by,
        )
        self._session.add(wo)
        await self._session.flush()  # get wo.id

        # 4. Snapshot BOM lines → work_order_materials
        for line in bom.lines:
            if line.material_id and not line.is_deleted:
                mat = WorkOrderMaterialModel(
                    work_order_id=wo.id,
                    material_id=line.material_id,
                    unit_id=line.unit_id,
                    required_quantity=float(Decimal(str(line.quantity)) * cmd.planned_quantity),
                    issued_quantity=0,
                )
                self._session.add(mat)

        # 5. Snapshot BOM operations → job_cards
        for op in sorted(bom.operations, key=lambda o: o.sequence):
            if not op.is_deleted:
                jc = JobCardModel(
                    work_order_id=wo.id,
                    operation_id=op.operation_id,
                    sequence=op.sequence,
                    status="PENDING",
                )
                self._session.add(jc)

        return wo.id

    # ── Release ─────────────────────────────────────────────────────────────────

    async def handle_release(self, cmd: ReleaseWorkOrderCommand) -> None:
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        entity = self._to_entity(wo)
        entity.release()
        wo.status = entity.status
        wo.updated_at = datetime.now(timezone.utc)
        
        # Emit event for dashboard notifications
        self._emit_event(WorkOrderReleased(
            aggregate_id=wo.id,
            tenant_id=cmd.tenant_id,
            event_type="work_order.released",
            wo_id=str(wo.id),
            wo_number=wo.wo_number,
            product=str(wo.product_id),
        ))

    # ── Start ───────────────────────────────────────────────────────────────────

    async def handle_start(self, cmd: StartWorkOrderCommand) -> None:
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        entity = self._to_entity(wo)
        entity.start()
        wo.status = entity.status
        wo.updated_at = datetime.now(timezone.utc)
        
        # Emit event for dashboard notifications
        self._emit_event(WorkOrderStarted(
            aggregate_id=wo.id,
            tenant_id=cmd.tenant_id,
            event_type="work_order.started",
            wo_id=str(wo.id),
            wo_number=wo.wo_number,
        ))

    # ── Issue Material ───────────────────────────────────────────────────────────

    async def handle_issue_material(self, cmd: IssueMaterialCommand) -> None:
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        entity = self._to_entity(wo)

        # Must be RELEASED or IN_PROGRESS
        if entity.status not in (WorkOrderStatus.RELEASED, WorkOrderStatus.IN_PROGRESS):
            from backend.app.domain.manufacturing.entities.work_order import InvalidStatusTransitionError
            raise InvalidStatusTransitionError(
                f"Cannot issue material with WO in status {entity.status}"
            )

        # Find material requirement
        mat_stmt = select(WorkOrderMaterialModel).where(
            WorkOrderMaterialModel.work_order_id == cmd.work_order_id,
            WorkOrderMaterialModel.material_id == cmd.material_id,
        )
        result = await self._session.execute(mat_stmt)
        req = result.scalar_one_or_none()
        if not req:
            raise ValueError(f"Material {cmd.material_id} is not in the WO material requirements")

        remaining = Decimal(str(req.required_quantity)) - Decimal(str(req.issued_quantity))
        if cmd.quantity > remaining:
            raise ValueError(
                f"Cannot issue {cmd.quantity}: only {remaining} remaining for this material requirement"
            )

        # Issue via InventoryService (SELECT FOR UPDATE + audit)
        await self._inventory.issue_stock(
            tenant_id=cmd.tenant_id,
            material_id=cmd.material_id,
            quantity=cmd.quantity,
            work_order_id=cmd.work_order_id,
            unit_id=cmd.unit_id,
            created_by=cmd.issued_by,
        )

        req.issued_quantity = float(Decimal(str(req.issued_quantity)) + cmd.quantity)

    # ── Record Production ────────────────────────────────────────────────────────

    async def handle_record_production(self, cmd: RecordProductionCommand) -> None:
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)

        rec = ProductionRecordModel(
            work_order_id=wo.id,
            produced_quantity=float(cmd.produced_quantity),
            scrap_quantity=float(cmd.scrap_quantity),
            recorded_by=cmd.recorded_by,
            notes=cmd.notes,
        )
        self._session.add(rec)

        new_produced = Decimal(str(wo.produced_quantity)) + cmd.produced_quantity
        new_scrap = Decimal(str(wo.scrap_quantity)) + cmd.scrap_quantity
        wo.produced_quantity = float(new_produced)
        wo.scrap_quantity = float(new_scrap)
        wo.updated_at = datetime.now(timezone.utc)

        # Resolve the finished-goods material_id.
        # WO.product_id is an item_variant UUID; inventory is tracked on MaterialModel.
        # We look for a material whose item_variant_id matches.
        from backend.app.infrastructure.persistence.models.material_model import MaterialModel
        mat_stmt = select(MaterialModel).where(
            MaterialModel.item_variant_id == wo.product_id,
            MaterialModel.tenant_id == wo.tenant_id,
            MaterialModel.is_deleted.is_(False),
        ).limit(1)
        mat_result = await self._session.execute(mat_stmt)
        fg_material = mat_result.scalar_one_or_none()

        if fg_material is None:
            # Fallback: no linked material found — skip inventory update but log warning.
            # This keeps production recording from failing if FG material isn't set up.
            import logging
            logging.getLogger(__name__).warning(
                "WO %s: no material linked to product_id %s — skipping FG inventory receipt.",
                wo.id, wo.product_id,
            )
            return

        # --- Consume component materials according to BOM lines ---
        # For each BOM line with a linked material, ensure cumulative consumption
        # equals (produced + scrap) * per-unit quantity. Issue any shortfall.
        from backend.app.infrastructure.persistence.models.bom_model import BOMLineModel

        total_output = Decimal(str(wo.produced_quantity)) + Decimal(str(wo.scrap_quantity))
        if wo.bom_id is not None:
            bl_stmt = (
                select(BOMLineModel)
                .where(
                    BOMLineModel.bom_id == wo.bom_id,
                    BOMLineModel.material_id.isnot(None),
                    BOMLineModel.is_deleted.is_(False),
                )
            )
            bl_res = await self._session.execute(bl_stmt)
            bom_lines = bl_res.scalars().all()
            for line in bom_lines:
                per_unit = Decimal(str(line.quantity))
                cumulative_required = total_output * per_unit

                # load the WO material requirement row
                wm_stmt = select(WorkOrderMaterialModel).where(
                    WorkOrderMaterialModel.work_order_id == wo.id,
                    WorkOrderMaterialModel.material_id == line.material_id,
                )
                wm_res = await self._session.execute(wm_stmt)
                wm = wm_res.scalar_one_or_none()
                if wm is None:
                    # no requirement tracked (unexpected) — skip
                    continue

                already_issued = Decimal(str(wm.issued_quantity))
                to_issue = cumulative_required - already_issued
                if to_issue > 0:
                    # perform inventory issuance (may raise InsufficientStockError)
                    await self._inventory.issue_stock(
                        tenant_id=cmd.tenant_id,
                        material_id=line.material_id,
                        quantity=to_issue,
                        work_order_id=wo.id,
                        unit_id=line.unit_id,
                        created_by=cmd.recorded_by,
                    )
                    wm.issued_quantity = float(already_issued + to_issue)

        # --- Receive finished goods into inventory ---
        await self._inventory.receive_stock(
            tenant_id=cmd.tenant_id,
            material_id=fg_material.id,  # FIXED: use material.id, not product_id
            quantity=cmd.produced_quantity,
            work_order_id=wo.id,
            created_by=cmd.recorded_by,
        )

    # ── Complete ─────────────────────────────────────────────────────────────────

    async def handle_complete(self, cmd: CompleteWorkOrderCommand) -> None:
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        entity = self._to_entity(wo)
        entity.complete()  # raises MaterialNotIssuedError if produced_qty == 0
        wo.status = entity.status
        wo.updated_at = datetime.now(timezone.utc)
        
        # Emit event for dashboard notifications
        self._emit_event(WorkOrderCompleted(
            aggregate_id=wo.id,
            tenant_id=cmd.tenant_id,
            event_type="work_order.completed",
            wo_id=str(wo.id),
            wo_number=wo.wo_number,
            produced_qty=float(wo.produced_quantity),
        ))

    # ── Close ────────────────────────────────────────────────────────────────────

    async def handle_close(self, cmd: CloseWorkOrderCommand) -> None:
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        entity = self._to_entity(wo)
        entity.close()
        wo.status = entity.status
        wo.updated_at = datetime.now(timezone.utc)
        
        # Emit event for dashboard notifications
        self._emit_event(WorkOrderClosed(
            aggregate_id=wo.id,
            tenant_id=cmd.tenant_id,
            event_type="work_order.closed",
            wo_id=str(wo.id),
            wo_number=wo.wo_number,
        ))

    # ── Job Card ─────────────────────────────────────────────────────────────────

    async def handle_start_job_card(self, cmd: StartJobCardCommand) -> None:
        jc = await self._get_job_card(cmd.job_card_id, cmd.work_order_id, cmd.tenant_id)
        if jc.status != "PENDING":
            raise ValueError(f"Job card is already {jc.status}")
        jc.status = "IN_PROGRESS"
        jc.started_at = datetime.now(timezone.utc)
        if cmd.assigned_to:
            jc.assigned_to = cmd.assigned_to

    async def handle_complete_job_card(self, cmd: CompleteJobCardCommand) -> None:
        jc = await self._get_job_card(cmd.job_card_id, cmd.work_order_id, cmd.tenant_id)
        if jc.status != "IN_PROGRESS":
            raise ValueError(f"Job card must be IN_PROGRESS to complete, current: {jc.status}")
        jc.status = "DONE"
        jc.completed_at = datetime.now(timezone.utc)
        if cmd.remarks:
            jc.remarks = cmd.remarks

    # ── Helpers ──────────────────────────────────────────────────────────────────

    async def _get_wo(self, work_order_id: uuid.UUID, tenant_id: uuid.UUID) -> WorkOrderModel:
        # SELECT FOR UPDATE: prevents concurrent status-transition race conditions
        stmt = (
            select(WorkOrderModel)
            .where(
                WorkOrderModel.id == work_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        wo = result.scalar_one_or_none()
        if not wo:
            raise ValueError(f"Work Order {work_order_id} not found")
        return wo

    async def _get_job_card(self, jc_id: uuid.UUID, wo_id: uuid.UUID, tenant_id: uuid.UUID) -> JobCardModel:
        # Validate tenant via WO ownership
        await self._get_wo(wo_id, tenant_id)
        stmt = select(JobCardModel).where(
            JobCardModel.id == jc_id, JobCardModel.work_order_id == wo_id
        )
        result = await self._session.execute(stmt)
        jc = result.scalar_one_or_none()
        if not jc:
            raise ValueError(f"Job Card {jc_id} not found")
        return jc

    def _to_entity(self, model: WorkOrderModel) -> WorkOrder:
        return WorkOrder(
            id=model.id,
            tenant_id=model.tenant_id,
            wo_number=model.wo_number,
            product_id=model.product_id,
            bom_id=model.bom_id,
            planned_quantity=Decimal(str(model.planned_quantity)),
            produced_quantity=Decimal(str(model.produced_quantity)),
            scrap_quantity=Decimal(str(model.scrap_quantity)),
            start_date=model.start_date,
            due_date=model.due_date,
            status=WorkOrderStatus(model.status),
            priority=WorkOrderPriority(model.priority),
            sales_order_id=model.sales_order_id,
            notes=model.notes,
            created_by=model.created_by,
        )
