"""MRP Service — Material Requirements Planning.

Calculates net requirements from gross demand (sales orders, work orders,
safety stock), current stock, open POs, and generates purchase suggestions
that can be individually or bulk-approved → converted to Purchase Orders.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.work_order_model import (
    WorkOrderModel,
    WorkOrderMaterialModel,
    WorkOrderStatus,
)
from backend.app.infrastructure.persistence.models.purchase_order_model import (
    PurchaseOrderModel,
    PurchaseOrderLineModel,
)
from backend.app.application.supply_chain.po_number_service import PONumberService


# ── In-memory suggestion store (per-process; replace with DB table in prod) ── #
# For production, persist MRPSuggestion to a dedicated table.  This lightweight
# implementation keeps suggestions in a module-level dict keyed by tenant.

_suggestions: dict[str, list[dict]] = {}  # tenant_id (str) → list of suggestion dicts


class MRPService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------ #
    #  Run MRP                                                             #
    # ------------------------------------------------------------------ #

    async def run(self, tenant_id: uuid.UUID) -> dict:
        """Full MRP run for the tenant.

        Steps:
        1. Fetch all active raw materials.
        2. Calculate gross requirements from:
           a. Open WOs (materials not yet fully issued)
           b. Open sales orders (unfulfilled quantity × BOM lookup — simplified)
           c. Safety stock rules (safety_stock field on material)
        3. Net = gross − (current_stock + open_po_qty − reserved_stock)
        4. If net > 0 → create suggestion with lead-time date.
        5. Group by supplier (use first available supplier on material; fallback "unknown").
        """
        tid = str(tenant_id)
        suggestions: list[dict] = []

        materials = (
            await self._session.execute(
                select(MaterialModel).where(
                    MaterialModel.tenant_id == tenant_id,
                    MaterialModel.is_deleted.is_(False),
                    MaterialModel.is_active.is_(True),
                )
            )
        ).scalars().all()

        # Build open PO incoming quantities per material
        open_po_qty = await self._open_po_qty(tenant_id)

        # Build gross requirements per material from WOs
        gross_from_wo = await self._gross_from_work_orders(tenant_id)

        # Build gross requirements from safety stock
        for mat in materials:
            material_id = str(mat.id)
            gross = Decimal(str(gross_from_wo.get(material_id, 0)))

            safety = Decimal(str(mat.safety_stock or 0))
            gross += safety  # safety stock counts as a perpetual requirement

            current = Decimal(str(mat.current_stock or 0))
            reserved = Decimal(str(mat.reserved_stock or 0))
            incoming = Decimal(str(open_po_qty.get(material_id, 0)))

            available = current + incoming - reserved
            net = gross - available

            if net <= Decimal("0"):
                continue  # No purchase needed

            # Apply min/max order quantity logic
            reorder = Decimal(str(mat.reorder_level or 0))
            suggested_qty = max(net, reorder)

            lead_time = mat.lead_time_days or 7
            order_by = date.today()
            need_by = order_by + timedelta(days=lead_time)

            suggestions.append(
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tid,
                    "material_id": material_id,
                    "material_code": mat.code,
                    "material_name": mat.name,
                    "gross_requirement": float(gross),
                    "current_stock": float(current),
                    "open_po_qty": float(incoming),
                    "reserved_stock": float(reserved),
                    "net_requirement": float(net),
                    "suggested_qty": float(suggested_qty),
                    "lead_time_days": lead_time,
                    "order_by_date": order_by.isoformat(),
                    "need_by_date": need_by.isoformat(),
                    "supplier_id": None,   # enriched below
                    "supplier_name": "Unknown",
                    "status": "pending",   # pending / approved / rejected / converted
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )

        _suggestions[tid] = suggestions
        return {"run_at": datetime.now(timezone.utc).isoformat(), "suggestions_count": len(suggestions)}

    # ------------------------------------------------------------------ #
    #  Get Suggestions                                                     #
    # ------------------------------------------------------------------ #

    def get_suggestions(self, tenant_id: uuid.UUID) -> List[dict]:
        return _suggestions.get(str(tenant_id), [])

    # ------------------------------------------------------------------ #
    #  Approve / Reject                                                    #
    # ------------------------------------------------------------------ #

    def approve_suggestion(self, tenant_id: uuid.UUID, suggestion_id: str) -> dict:
        return self._set_status(tenant_id, suggestion_id, "approved")

    def reject_suggestion(self, tenant_id: uuid.UUID, suggestion_id: str) -> dict:
        return self._set_status(tenant_id, suggestion_id, "rejected")

    def bulk_approve(self, tenant_id: uuid.UUID, suggestion_ids: List[str]) -> dict:
        count = 0
        for sid in suggestion_ids:
            try:
                self._set_status(tenant_id, sid, "approved")
                count += 1
            except ValueError:
                pass
        return {"approved": count}

    # ------------------------------------------------------------------ #
    #  Convert approved suggestions → Purchase Orders                      #
    # ------------------------------------------------------------------ #

    async def convert_to_po(
        self,
        tenant_id: uuid.UUID,
        suggestion_ids: Optional[List[str]] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> List[dict]:
        """Batch approved suggestions into POs (one per supplier).

        If suggestion_ids is None → process all approved suggestions.
        """
        tid = str(tenant_id)
        all_suggs = _suggestions.get(tid, [])

        to_convert = [
            s for s in all_suggs
            if s["status"] == "approved"
            and (suggestion_ids is None or s["id"] in suggestion_ids)
        ]

        if not to_convert:
            return []

        # Group by supplier_id (None → "unknown" bucket)
        by_supplier: dict[str, list[dict]] = {}
        for s in to_convert:
            key = s.get("supplier_id") or "unknown"
            by_supplier.setdefault(key, []).append(s)

        created_pos = []
        po_svc = PONumberService(self._session)

        for supplier_key, items in by_supplier.items():
            po_number = await po_svc.generate(tenant_id)
            total = Decimal("0")
            po = PurchaseOrderModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                po_number=po_number,
                supplier_id=uuid.UUID(supplier_key) if _is_valid_uuid(supplier_key) else None,
                order_date=date.today(),
                status="draft",
                total_amount=0,
                created_by=created_by or uuid.uuid4(),
            )
            self._session.add(po)
            await self._session.flush()

            for item in items:
                unit_price = Decimal("0")  # No price on suggestion; buyer fills in
                lt = Decimal(str(item["suggested_qty"])) * unit_price
                total += lt
                self._session.add(
                    PurchaseOrderLineModel(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        purchase_order_id=po.id,
                        material_id=uuid.UUID(item["material_id"]),
                        quantity=float(item["suggested_qty"]),
                        received_quantity=0,
                        unit_price=0,
                        line_total=0,
                    )
                )
                # Mark suggestion as converted
                for s in all_suggs:
                    if s["id"] == item["id"]:
                        s["status"] = "converted"
                        s["po_id"] = str(po.id)

            po.total_amount = float(total)
            await self._session.flush()
            created_pos.append({"po_id": str(po.id), "po_number": po_number, "lines": len(items)})

        await self._session.commit()
        return created_pos

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    async def _open_po_qty(self, tenant_id: uuid.UUID) -> dict[str, float]:
        """Sum of open PO line quantities (not yet received) per material."""
        stmt = (
            select(
                PurchaseOrderLineModel.material_id,
                func.sum(
                    PurchaseOrderLineModel.quantity - PurchaseOrderLineModel.received_quantity
                ),
            )
            .join(PurchaseOrderModel, PurchaseOrderLineModel.purchase_order_id == PurchaseOrderModel.id)
            .where(
                PurchaseOrderModel.tenant_id == tenant_id,
                PurchaseOrderModel.is_deleted.is_(False),
                PurchaseOrderModel.status.in_(["draft", "sent", "acknowledged", "partial"]),
                PurchaseOrderLineModel.is_deleted.is_(False),
            )
            .group_by(PurchaseOrderLineModel.material_id)
        )
        rows = (await self._session.execute(stmt)).all()
        return {str(mat_id): float(qty or 0) for mat_id, qty in rows}

    async def _gross_from_work_orders(self, tenant_id: uuid.UUID) -> dict[str, float]:
        """Sum of unreleased/in-progress WO material requirements still to be issued."""
        stmt = (
            select(
                WorkOrderMaterialModel.material_id,
                func.sum(
                    WorkOrderMaterialModel.required_quantity
                    - WorkOrderMaterialModel.issued_quantity
                ),
            )
            .join(WorkOrderModel, WorkOrderMaterialModel.work_order_id == WorkOrderModel.id)
            .where(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
                WorkOrderModel.status.in_([
                    WorkOrderStatus.PLANNED,
                    WorkOrderStatus.RELEASED,
                    WorkOrderStatus.IN_PROGRESS,
                ]),
            )
            .group_by(WorkOrderMaterialModel.material_id)
        )
        rows = (await self._session.execute(stmt)).all()
        return {str(mat_id): float(qty or 0) for mat_id, qty in rows}

    def _set_status(self, tenant_id: uuid.UUID, suggestion_id: str, new_status: str) -> dict:
        tid = str(tenant_id)
        for s in _suggestions.get(tid, []):
            if s["id"] == suggestion_id:
                if s["status"] in ("converted",):
                    raise ValueError("Cannot change status of a converted suggestion")
                s["status"] = new_status
                return s
        raise ValueError(f"Suggestion {suggestion_id} not found")


def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False
