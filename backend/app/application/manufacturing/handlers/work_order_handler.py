"""
WorkOrderHandler — orchestrates all Work Order use cases.

Data flow: API → Command → Handler → Domain Entity + Services → Repository → DB
"""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.application.manufacturing.commands.work_order_commands import (
    CreateWorkOrderCommand, ReleaseWorkOrderCommand, StartWorkOrderCommand,
    IssueMaterialCommand, RecordProductionCommand,
    CompleteWorkOrderCommand, CloseWorkOrderCommand,
    StartJobCardCommand, CompleteJobCardCommand,
    QCApproveCommand, QCRejectCommand, QCSendToReworkCommand, FGReceiveCommand,
)
from backend.app.application.manufacturing.services.inventory_service import InventoryService
from backend.app.application.manufacturing.services.wo_number_service import WONumberService
from backend.app.application.inventory.services.inventory_reservation_service import InventoryReservationService
from backend.app.domain.manufacturing.entities.work_order import WorkOrder, WorkOrderStatus, WorkOrderPriority
from backend.app.domain.manufacturing.exceptions import BOMNotFoundError
from backend.app.domain.manufacturing.events.work_order_events import (
    WorkOrderReleased, WorkOrderStarted, WorkOrderCompleted, WorkOrderClosed,
)
from backend.app.infrastructure.persistence.models.work_order_model import (
    WorkOrderModel, WorkOrderMaterialModel, JobCardModel, ProductionRecordModel
)
from backend.app.infrastructure.persistence.models.bom_model import BOMModel

logger = logging.getLogger(__name__)


class WorkOrderHandler:
    def __init__(self, session: AsyncSession, uow=None):
        self._session = session
        self._uow = uow  # Optional: UnitOfWork for emitting domain events
        self._inventory = InventoryService(session)
        self._reservation = InventoryReservationService(session)
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
            sales_order_line_id=cmd.sales_order_line_id,
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

        # Keep the freshly snapshotted materials visible for same-transaction release planning.
        await self._session.flush()
        return wo.id

    # ── Release ─────────────────────────────────────────────────────────────────

    async def handle_release(self, cmd: ReleaseWorkOrderCommand) -> None:
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        entity = self._to_entity(wo)
        entity.release()
        wo.status = entity.status
        wo.updated_at = datetime.now(timezone.utc)

        # Transition to MATERIAL_PENDING and trigger material planning
        wo.status = WorkOrderStatus.MATERIAL_PENDING
        await self._plan_materials_for_release(wo)

        # Emit event for dashboard notifications
        self._emit_event(WorkOrderReleased(
            aggregate_id=wo.id,
            tenant_id=cmd.tenant_id,
            event_type="work_order.released",
            wo_id=str(wo.id),
            wo_number=wo.wo_number,
            product=str(wo.product_id),
        ))

    async def _plan_materials_for_release(self, wo: WorkOrderModel) -> None:
        """Reserve available BOM material and procure net shortage for this WO."""
        from backend.app.application.supply_chain.po_number_service import PONumberService
        from backend.app.infrastructure.persistence.models.material_model import MaterialModel
        from backend.app.infrastructure.persistence.models.material_request_model import MaterialRequestModel
        from backend.app.infrastructure.persistence.models.purchase_order_model import (
            PurchaseOrderLineModel,
            PurchaseOrderModel,
        )
        from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel

        rows = (
            await self._session.execute(
                select(WorkOrderMaterialModel, MaterialModel)
                .join(MaterialModel, MaterialModel.id == WorkOrderMaterialModel.material_id)
                .where(
                    WorkOrderMaterialModel.work_order_id == wo.id,
                    MaterialModel.tenant_id == wo.tenant_id,
                    MaterialModel.is_deleted.is_(False),
                )
            )
        ).all()
        if not rows:
            return

        shortage_lines: list[tuple[WorkOrderMaterialModel, MaterialModel, Decimal]] = []
        for requirement, material in rows:
            required_qty = Decimal(str(requirement.required_quantity or 0))
            issued_qty = Decimal(str(requirement.issued_quantity or 0))
            remaining_qty = required_qty - issued_qty
            if remaining_qty <= 0:
                continue

            available_qty = await self._inventory.get_available_stock(
                tenant_id=wo.tenant_id,
                material_id=material.id,
            )
            reserve_qty = min(remaining_qty, available_qty)
            if reserve_qty > 0:
                # Use new reservation service with partial reservation handling
                reserved_qty, shortage_qty, shortage_record_id = await self._reservation.reserve_for_work_order(
                    tenant_id=wo.tenant_id,
                    work_order_id=wo.id,
                    material_id=material.id,
                    required_quantity=remaining_qty,
                    unit_id=requirement.unit_id,
                    created_by=wo.created_by,
                )
            else:
                shortage_qty = remaining_qty

            # Check for net shortage after considering incoming POs
            incoming_qty = await self._open_po_quantity(wo.tenant_id, material.id)
            net_shortage_qty = shortage_qty - incoming_qty
            if net_shortage_qty > 0:
                shortage_lines.append((requirement, material, net_shortage_qty))

        # If no shortages and reservations successful, transition to MATERIAL_RESERVED
        if not shortage_lines:
            wo.status = WorkOrderStatus.MATERIAL_RESERVED
            wo.updated_at = datetime.now(timezone.utc)
            return

        for requirement, material, shortage_qty in shortage_lines:
            existing_request = (
                await self._session.execute(
                    select(MaterialRequestModel).where(
                        MaterialRequestModel.tenant_id == wo.tenant_id,
                        MaterialRequestModel.item_id == material.id,
                        MaterialRequestModel.item_type == "material",
                        MaterialRequestModel.source_ref_type == "work_order",
                        MaterialRequestModel.source_ref_id == wo.id,
                        MaterialRequestModel.status == "open",
                        MaterialRequestModel.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()

            if existing_request is None:
                self._session.add(
                    MaterialRequestModel(
                        id=uuid.uuid4(),
                        tenant_id=wo.tenant_id,
                        item_id=material.id,
                        item_type="material",
                        required_quantity=float(shortage_qty),
                        fulfilled_quantity=0,
                        required_by=wo.due_date,
                        status="open",
                        source_ref_type="work_order",
                        source_ref_id=wo.id,
                    )
                )
            elif shortage_qty > Decimal(str(existing_request.required_quantity or 0)):
                existing_request.required_quantity = float(shortage_qty)
                existing_request.required_by = wo.due_date

        supplier_groups: dict[
            uuid.UUID,
            tuple[SupplierModel, list[tuple[WorkOrderMaterialModel, MaterialModel, Decimal]]],
        ] = {}
        for requirement, material, shortage_qty in shortage_lines:
            supplier = await self._choose_supplier_for_material(wo.tenant_id, material.id)
            if supplier is None:
                logger.warning(
                    "WO %s has material shortage for %s but no active supplier is available.",
                    wo.id,
                    material.id,
                )
                continue

            _, grouped_lines = supplier_groups.setdefault(supplier.id, (supplier, []))
            grouped_lines.append((requirement, material, shortage_qty))

        for supplier, grouped_lines in supplier_groups.values():
            po_total = Decimal("0")
            po_number = await PONumberService(self._session).generate(wo.tenant_id)
            po = PurchaseOrderModel(
                id=uuid.uuid4(),
                tenant_id=wo.tenant_id,
                po_number=po_number,
                supplier_id=supplier.id,
                order_date=date.today(),
                expected_delivery=wo.due_date,
                status="sent",
                total_amount=0,
                notes=f"Auto-created for WO {wo.id} raw-material shortage.",
                created_by=wo.created_by,
            )
            self._session.add(po)
            await self._session.flush()

            for _, material, shortage_qty in grouped_lines:
                unit_price = Decimal(str(material.current_cost or 0))
                line_total = shortage_qty * unit_price
                po_total += line_total
                self._session.add(
                    PurchaseOrderLineModel(
                        id=uuid.uuid4(),
                        tenant_id=wo.tenant_id,
                        purchase_order_id=po.id,
                        material_id=material.id,
                        quantity=float(shortage_qty),
                        received_quantity=0,
                        unit_price=float(unit_price),
                        line_total=float(line_total),
                    )
                )

            po.total_amount = float(po_total)

    async def _open_po_quantity(self, tenant_id: uuid.UUID, material_id: uuid.UUID) -> Decimal:
        from backend.app.infrastructure.persistence.models.purchase_order_model import (
            PurchaseOrderLineModel,
            PurchaseOrderModel,
        )

        result = await self._session.execute(
            select(
                func.coalesce(
                    func.sum(PurchaseOrderLineModel.quantity - PurchaseOrderLineModel.received_quantity),
                    0,
                )
            )
            .join(PurchaseOrderModel, PurchaseOrderModel.id == PurchaseOrderLineModel.purchase_order_id)
            .where(
                PurchaseOrderModel.tenant_id == tenant_id,
                PurchaseOrderModel.status.in_(["draft", "sent", "acknowledged", "partial"]),
                PurchaseOrderModel.is_deleted.is_(False),
                PurchaseOrderLineModel.material_id == material_id,
                PurchaseOrderLineModel.is_deleted.is_(False),
            )
        )
        return Decimal(str(result.scalar_one() or 0))

    async def _choose_supplier_for_material(self, tenant_id: uuid.UUID, material_id: uuid.UUID):
        from backend.app.infrastructure.persistence.models.supplier_model import (
            SupplierModel,
            SupplierPriceHistoryModel,
        )

        preferred = (
            await self._session.execute(
                select(SupplierModel)
                .join(SupplierPriceHistoryModel, SupplierPriceHistoryModel.supplier_id == SupplierModel.id)
                .where(
                    SupplierModel.tenant_id == tenant_id,
                    SupplierModel.is_active.is_(True),
                    SupplierModel.is_deleted.is_(False),
                    SupplierPriceHistoryModel.tenant_id == tenant_id,
                    SupplierPriceHistoryModel.material_id == material_id,
                )
                .order_by(
                    SupplierPriceHistoryModel.effective_from.desc(),
                    SupplierPriceHistoryModel.created_at.desc(),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if preferred is not None:
            return preferred

        from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel

        return (
            await self._session.execute(
                select(SupplierModel)
                .where(
                    SupplierModel.tenant_id == tenant_id,
                    SupplierModel.is_active.is_(True),
                    SupplierModel.is_deleted.is_(False),
                )
                .order_by(SupplierModel.created_at.asc())
                .limit(1)
            )
        ).scalar_one_or_none()

    # ── Start ───────────────────────────────────────────────────────────────────

    async def handle_start(self, cmd: StartWorkOrderCommand) -> None:
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        entity = self._to_entity(wo)
        entity.start()
        wo.status = entity.status
        wo.updated_at = datetime.now(timezone.utc)

        # Transition to IN_PRODUCTION (from MATERIAL_ISSUED)
        wo.status = WorkOrderStatus.IN_PRODUCTION
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

        # Must be MATERIAL_RESERVED or MATERIAL_ISSUED (for partial issues)
        if entity.status not in (WorkOrderStatus.MATERIAL_RESERVED, WorkOrderStatus.MATERIAL_ISSUED):
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

        # Check if all materials are now issued, transition to MATERIAL_ISSUED if not already
        all_materials_stmt = select(WorkOrderMaterialModel).where(
            WorkOrderMaterialModel.work_order_id == cmd.work_order_id
        )
        all_materials_result = await self._session.execute(all_materials_stmt)
        all_materials = all_materials_result.scalars().all()

        all_issued = all(
            Decimal(str(m.issued_quantity)) >= Decimal(str(m.required_quantity))
            for m in all_materials
        )

        if all_issued and entity.status == WorkOrderStatus.MATERIAL_RESERVED:
            wo.status = WorkOrderStatus.MATERIAL_ISSUED
            wo.updated_at = datetime.now(timezone.utc)
        elif entity.status == WorkOrderStatus.MATERIAL_RESERVED:
            wo.status = WorkOrderStatus.MATERIAL_ISSUED
            wo.updated_at = datetime.now(timezone.utc)

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

        # Resolve the finished-goods material_id. Older schemas do not have an
        # item_variant_id column, so mirror product search: first try a material
        # with the variant UUID, then a finished material with the variant code.
        from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
        from backend.app.infrastructure.persistence.models.material_model import MaterialModel

        mat_stmt = select(MaterialModel).where(
            MaterialModel.id == wo.product_id,
            MaterialModel.tenant_id == wo.tenant_id,
            MaterialModel.is_deleted.is_(False),
        ).limit(1)
        mat_result = await self._session.execute(mat_stmt)
        fg_material = mat_result.scalar_one_or_none()

        if fg_material is None:
            variant_stmt = select(ItemVariantModel).where(
                ItemVariantModel.id == wo.product_id,
                ItemVariantModel.tenant_id == wo.tenant_id,
                ItemVariantModel.is_deleted.is_(False),
            ).limit(1)
            variant_result = await self._session.execute(variant_stmt)
            variant = variant_result.scalar_one_or_none()

            if variant is not None:
                if getattr(variant, "material_id", None):
                    mapped_stmt = select(MaterialModel).where(
                        MaterialModel.id == variant.material_id,
                        MaterialModel.tenant_id == wo.tenant_id,
                        MaterialModel.is_deleted.is_(False),
                    ).limit(1)
                    mapped_result = await self._session.execute(mapped_stmt)
                    fg_material = mapped_result.scalar_one_or_none()

                if fg_material is None:
                    code_stmt = select(MaterialModel).where(
                        MaterialModel.tenant_id == wo.tenant_id,
                        MaterialModel.code == variant.code,
                        MaterialModel.material_type == "finished",
                        MaterialModel.is_deleted.is_(False),
                    ).limit(1)
                    code_result = await self._session.execute(code_stmt)
                    fg_material = code_result.scalar_one_or_none()

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
                if to_issue > 0 and line.material_id is not None:
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
        await self._reserve_produced_goods_for_sales(
            tenant_id=cmd.tenant_id,
            work_order=wo,
            finished_material_id=fg_material.id,
            produced_quantity=cmd.produced_quantity,
            recorded_by=cmd.recorded_by,
        )

    # ── Complete ─────────────────────────────────────────────────────────────────

    async def handle_complete(self, cmd: CompleteWorkOrderCommand) -> None:
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        entity = self._to_entity(wo)
        entity.complete()  # raises MaterialNotIssuedError if produced_qty == 0
        wo.status = entity.status
        wo.updated_at = datetime.now(timezone.utc)

        # Transition to QC_PENDING instead of COMPLETED
        wo.status = WorkOrderStatus.QC_PENDING
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

    async def _reserve_produced_goods_for_sales(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order: WorkOrderModel,
        finished_material_id: uuid.UUID,
        produced_quantity: Decimal,
        recorded_by: uuid.UUID,
    ) -> None:
        """Allocate newly produced finished goods back to the linked sales line."""
        if not work_order.sales_order_line_id:
            return

        from backend.app.infrastructure.persistence.models.sales_models import (
            SalesOrderLineModel,
            SalesOrderModel,
        )

        line_result = await self._session.execute(
            select(SalesOrderLineModel).where(
                SalesOrderLineModel.id == work_order.sales_order_line_id,
            )
        )
        line = line_result.scalar_one_or_none()
        if line is None:
            return

        backorder_qty = Decimal(str(line.backorder_quantity or 0))
        reserve_qty = min(produced_quantity, backorder_qty)
        if reserve_qty <= 0:
            return

        await self._inventory.reserve_sales_stock(
            tenant_id=tenant_id,
            material_id=finished_material_id,
            quantity=reserve_qty,
            sales_order_line_id=line.id,
            unit_id=line.uom_id,
            created_by=recorded_by,
        )

        line.allocated_quantity = float(Decimal(str(line.allocated_quantity or 0)) + reserve_qty)
        line.backorder_quantity = float(max(Decimal("0"), backorder_qty - reserve_qty))
        line.status = "allocated" if Decimal(str(line.backorder_quantity or 0)) <= 0 else "backorder"
        line.updated_at = datetime.now(timezone.utc)

        order = await self._session.get(SalesOrderModel, line.sales_order_id)
        if order is None or order.tenant_id != tenant_id:
            return

        lines = (
            await self._session.execute(
                select(SalesOrderLineModel).where(SalesOrderLineModel.sales_order_id == order.id)
            )
        ).scalars().all()
        all_allocated = bool(lines) and all(
            Decimal(str(order_line.allocated_quantity or 0)) >= Decimal(str(order_line.quantity or 0))
            for order_line in lines
        )
        if all_allocated:
            order.status = "READY"
        elif order.status in ("CONFIRMED", "PROCESSING"):
            order.status = "PRODUCTION"
        order.updated_at = datetime.now(timezone.utc)

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

    # ── QC Operations ─────────────────────────────────────────────────────────────

    async def handle_qc_approve(self, cmd: QCApproveCommand) -> None:
        """Approve QC inspection and transition to FG_RECEIVED."""
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        entity = self._to_entity(wo)

        if entity.status != WorkOrderStatus.QC_PENDING:
            from backend.app.domain.manufacturing.entities.work_order import InvalidStatusTransitionError
            raise InvalidStatusTransitionError(
                f"Cannot approve QC: WO must be in QC_PENDING status, current: {entity.status}"
            )

        wo.status = WorkOrderStatus.QC_APPROVED
        wo.updated_at = datetime.now(timezone.utc)

    async def handle_qc_reject(self, cmd: QCRejectCommand) -> None:
        """Reject QC inspection and transition to REWORK or REJECTED."""
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        entity = self._to_entity(wo)

        if entity.status != WorkOrderStatus.QC_PENDING:
            from backend.app.domain.manufacturing.entities.work_order import InvalidStatusTransitionError
            raise InvalidStatusTransitionError(
                f"Cannot reject QC: WO must be in QC_PENDING status, current: {entity.status}"
            )

        if cmd.send_to_rework:
            wo.status = WorkOrderStatus.REWORK
        else:
            wo.status = WorkOrderStatus.REJECTED
        wo.updated_at = datetime.now(timezone.utc)

    async def handle_qc_send_to_rework(self, cmd: QCSendToReworkCommand) -> None:
        """Send rejected WO to rework."""
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        entity = self._to_entity(wo)

        if entity.status != WorkOrderStatus.REJECTED:
            from backend.app.domain.manufacturing.entities.work_order import InvalidStatusTransitionError
            raise InvalidStatusTransitionError(
                f"Cannot send to rework: WO must be in REJECTED status, current: {entity.status}"
            )

        wo.status = WorkOrderStatus.REWORK
        wo.updated_at = datetime.now(timezone.utc)

    async def handle_fg_receive(self, cmd: FGReceiveCommand) -> None:
        """Receive finished goods after QC approval and transition to COMPLETED."""
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        entity = self._to_entity(wo)

        entity.require_qc_approved()

        wo.status = WorkOrderStatus.FG_RECEIVED
        wo.updated_at = datetime.now(timezone.utc)

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
            sales_order_line_id=model.sales_order_line_id,
            notes=model.notes,
            created_by=model.created_by,
        )
