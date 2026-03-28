from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import selectinload

from backend.app.application.manufacturing.services.inventory_service import InventoryService
from backend.app.application.supply_chain.po_number_service import PONumberService
from backend.app.application.supply_chain.subcontract_number_service import SubcontractNumberService
from backend.app.infrastructure.persistence.models.location_model import LocationModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.material_request_model import MaterialRequestModel
from backend.app.infrastructure.persistence.models.purchase_order_model import PurchaseOrderLineModel, PurchaseOrderModel
from backend.app.infrastructure.persistence.models.quality_model import (
    InspectionDetailModel,
    NonConformanceReportModel,
    QualityInspectionModel,
    SupplierQuotationModel,
)
from backend.app.infrastructure.persistence.models.stock_level_model import StockLevelModel
from backend.app.infrastructure.persistence.models.subcontract_model import SubcontractMaterialIssueModel, SubcontractOrderModel
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from backend.app.interfaces.api.v1.dependencies.auth import get_container, get_current_tenant_id, get_current_user_id
from backend.app.interfaces.api.v1.dependencies.supplier_portal import require_supplier_id
from backend.app.interfaces.api.v1.schemas.supply_chain_schemas import (
    GoodsReceiptRequest,
    NCRCreateRequest,
    PurchaseOrderCreate,
    QualityInspectRequest,
    SubcontractIssueRequest,
    SubcontractOrderCreate,
    SubcontractReceiveRequest,
    SupplierCreate,
    SupplierQuotationCreate,
    SupplierResponse,
    SupplierUpdate,
)

router = APIRouter(tags=["Supply Chain"])


def _po_to_dict(p: PurchaseOrderModel) -> dict:
    return {
        "id": str(p.id),
        "po_number": p.po_number,
        "supplier_id": str(p.supplier_id),
        "status": p.status,
        "order_date": p.order_date.isoformat(),
        "expected_delivery": p.expected_delivery.isoformat() if p.expected_delivery else None,
        "total_amount": float(p.total_amount),
        "notes": p.notes,
        "lines": [
            {
                "id": str(l.id),
                "material_id": str(l.material_id),
                "quantity": float(l.quantity),
                "received_quantity": float(l.received_quantity),
                "unit_price": float(l.unit_price),
                "line_total": float(l.line_total),
            }
            for l in p.lines
            if not l.is_deleted
        ],
    }


async def _first_quarantine_location(session, tenant_id: uuid.UUID) -> Optional[uuid.UUID]:
    stmt = (
        select(LocationModel.id)
        .where(
            LocationModel.tenant_id == tenant_id,
            LocationModel.type == "quarantine",
            LocationModel.is_deleted.is_(False),
            LocationModel.is_active.is_(True),
        )
        .limit(1)
    )
    r = await session.execute(stmt)
    return r.scalar_one_or_none()


async def _subcontractor_location(session, tenant_id: uuid.UUID, supplier_id: uuid.UUID) -> uuid.UUID:
    """Reuse or create a location row for this supplier (type subcontractor)."""
    code = f"SUB-{supplier_id}"
    stmt = select(LocationModel).where(
        LocationModel.tenant_id == tenant_id,
        LocationModel.code == code,
        LocationModel.is_deleted.is_(False),
    )
    r = await session.execute(stmt)
    loc = r.scalar_one_or_none()
    if loc:
        return loc.id
    sup = await session.get(SupplierModel, supplier_id)
    name = f"Subcontractor: {sup.code}" if sup else f"Subcontractor {supplier_id}"
    loc = LocationModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=name[:100],
        type="subcontractor",
        code=code,
        is_active=True,
    )
    session.add(loc)
    await session.flush()
    return loc.id


# ── Suppliers (tenant) ────────────────────────────────────────────────────────


@router.get("/suppliers", response_model=List[SupplierResponse])
async def list_suppliers(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(SupplierModel)
            .where(SupplierModel.tenant_id == tenant_id, SupplierModel.is_deleted.is_(False))
            .order_by(SupplierModel.code)
        )
        r = await session.execute(stmt)
        rows = r.scalars().all()
    return [SupplierResponse.model_validate(x) for x in rows]


@router.post("/suppliers", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    body: SupplierCreate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        exists = await session.execute(
            select(SupplierModel.id).where(
                SupplierModel.tenant_id == tenant_id,
                SupplierModel.code == body.code,
                SupplierModel.is_deleted.is_(False),
            )
        )
        if exists.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Supplier code already exists")
        s = SupplierModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            code=body.code,
            name=body.name,
            contact_person=body.contact_person,
            email=body.email,
            phone=body.phone,
            address=body.address,
            gst=body.gst,
            payment_terms=body.payment_terms,
        )
        session.add(s)
        await session.commit()
        await session.refresh(s)
    return SupplierResponse.model_validate(s)


@router.put("/suppliers/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: uuid.UUID,
    body: SupplierUpdate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        s = await session.get(SupplierModel, supplier_id)
        if not s or s.tenant_id != tenant_id or s.is_deleted:
            raise HTTPException(status_code=404, detail="Supplier not found")
        data = body.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(s, k, v)
        s.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(s)
    return SupplierResponse.model_validate(s)


# ── Purchase orders ───────────────────────────────────────────────────────────


@router.get("/purchase-orders")
async def list_purchase_orders(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(PurchaseOrderModel.tenant_id == tenant_id, PurchaseOrderModel.is_deleted.is_(False))
            .order_by(PurchaseOrderModel.created_at.desc())
        )
        r = await session.execute(stmt)
        pos = r.scalars().unique().all()
    return [_po_to_dict(p) for p in pos]


@router.get("/purchase-orders/{po_id}")
async def get_purchase_order(
    po_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(
                PurchaseOrderModel.id == po_id,
                PurchaseOrderModel.tenant_id == tenant_id,
                PurchaseOrderModel.is_deleted.is_(False),
            )
        )
        r = await session.execute(stmt)
        p = r.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="PO not found")
    return _po_to_dict(p)


@router.post("/purchase-orders", status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    body: PurchaseOrderCreate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        if not body.lines:
            raise HTTPException(status_code=400, detail="At least one PO line is required")
        po_svc = PONumberService(session)
        po_number = await po_svc.generate(tenant_id)
        total = Decimal("0")
        po = PurchaseOrderModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            po_number=po_number,
            supplier_id=body.supplier_id,
            order_date=date.today(),
            expected_delivery=body.expected_delivery,
            status="draft",
            total_amount=0,
            notes=body.notes,
            created_by=user_id,
        )
        session.add(po)
        await session.flush()
        for line in body.lines:
            lt = Decimal(str(line.quantity)) * Decimal(str(line.unit_price))
            total += lt
            pl = PurchaseOrderLineModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                purchase_order_id=po.id,
                material_id=line.material_id,
                quantity=float(line.quantity),
                received_quantity=0,
                unit_price=float(line.unit_price),
                line_total=float(lt),
            )
            session.add(pl)
        po.total_amount = float(total)
        await session.commit()
    return {"id": str(po.id), "po_number": po.po_number}


@router.put("/purchase-orders/{po_id}/send")
async def send_purchase_order(
    po_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        po = await session.get(PurchaseOrderModel, po_id)
        if not po or po.tenant_id != tenant_id or po.is_deleted:
            raise HTTPException(status_code=404, detail="PO not found")
        if po.status != "draft":
            raise HTTPException(status_code=400, detail="Only draft PO can be sent")
        po.status = "sent"
        po.updated_at = datetime.now(timezone.utc)
        await session.commit()
    return {"status": "ok"}


@router.put("/purchase-orders/{po_id}/acknowledge")
async def acknowledge_purchase_order(
    po_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        po = await session.get(PurchaseOrderModel, po_id)
        if not po or po.tenant_id != tenant_id or po.is_deleted:
            raise HTTPException(status_code=404, detail="PO not found")
        if po.status not in ("sent", "acknowledged", "partial"):
            raise HTTPException(status_code=400, detail="PO cannot be acknowledged from this status")
        po.status = "acknowledged"
        po.updated_at = datetime.now(timezone.utc)
        await session.commit()
    return {"status": "ok"}


@router.put("/purchase-orders/{po_id}/receive")
async def receive_goods(
    po_id: uuid.UUID,
    body: GoodsReceiptRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(
                PurchaseOrderModel.id == po_id,
                PurchaseOrderModel.tenant_id == tenant_id,
                PurchaseOrderModel.is_deleted.is_(False),
            )
            .with_for_update(of=PurchaseOrderModel)
        )
        r = await session.execute(stmt)
        po = r.scalar_one_or_none()
        if not po:
            raise HTTPException(status_code=404, detail="PO not found")
        if po.status not in ("sent", "acknowledged", "partial"):
            raise HTTPException(status_code=400, detail="PO not open for receiving")

        inv = InventoryService(session)

        for item in body.lines:
            lid = next((ln for ln in po.lines if ln.id == item.line_id and not ln.is_deleted), None)
            if not lid:
                raise HTTPException(status_code=400, detail=f"Line {item.line_id} not on PO")
            qty = Decimal(str(item.quantity))
            max_recv = Decimal(str(lid.quantity)) - Decimal(str(lid.received_quantity))
            if qty <= 0 or qty > max_recv:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid receive qty for line {lid.id}: max {max_recv}",
                )
            mat = await session.get(MaterialModel, lid.material_id)
            await inv.receive_purchase_receipt(
                tenant_id=tenant_id,
                material_id=lid.material_id,
                quantity=qty,
                purchase_order_id=po.id,
                unit_id=mat.base_unit_id if mat else None,
                created_by=user_id,
                warehouse_location_id=body.warehouse_location_id,
            )
            lid.received_quantity = float(Decimal(str(lid.received_quantity)) + qty)
            await session.execute(
                text("""
                    INSERT INTO supplier_price_history (
                        id, tenant_id, supplier_id, material_id, unit_price, effective_from, created_at
                    ) VALUES (
                        :id, :tid, :sid, :mid, :up, CURRENT_DATE, NOW()
                    )
                """),
                {
                    "id": str(uuid.uuid4()),
                    "tid": str(tenant_id),
                    "sid": str(po.supplier_id),
                    "mid": str(lid.material_id),
                    "up": float(lid.unit_price),
                },
            )

        # PO status
        all_done = all(
            Decimal(str(l.received_quantity)) >= Decimal(str(l.quantity))
            for l in po.lines
            if not l.is_deleted
        )
        any_recv = any(Decimal(str(l.received_quantity)) > 0 for l in po.lines if not l.is_deleted)
        if all_done:
            po.status = "received"
        elif any_recv:
            po.status = "partial"
        po.updated_at = datetime.now(timezone.utc)
        await session.commit()
    return {"status": "ok"}


# ── Quality ───────────────────────────────────────────────────────────────────


@router.post("/quality/inspect")
async def quality_inspect(
    body: QualityInspectRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        qi = QualityInspectionModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            reference_type=body.reference_type,
            reference_id=body.reference_id,
            inspection_date=date.today(),
            inspector_id=user_id,
            result=body.result,
            remarks=body.remarks,
        )
        session.add(qi)
        await session.flush()
        if body.details:
            for d in body.details:
                session.add(
                    InspectionDetailModel(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        inspection_id=qi.id,
                        parameter=str(d.get("parameter", "")),
                        measured_value=d.get("measured_value"),
                        tolerance_min=d.get("tolerance_min"),
                        tolerance_max=d.get("tolerance_max"),
                        is_passed=bool(d.get("is_passed", False)),
                    )
                )
        inv = InventoryService(session)
        if body.result == "pass":
            await inv.inspection_pass_move_to_available(
                tenant_id=tenant_id,
                material_id=body.material_id,
                quantity=body.quantity,
                warehouse_location_id=body.warehouse_location_id,
                inspection_id=qi.id,
                created_by=user_id,
            )
        elif body.result in ("fail", "rework"):
            q_loc = await _first_quarantine_location(session, tenant_id)
            if not q_loc:
                raise HTTPException(
                    status_code=400,
                    detail="No quarantine location (type=quarantine). Create one under Locations.",
                )
            await inv.inspection_fail_move_to_quarantine(
                tenant_id=tenant_id,
                material_id=body.material_id,
                quantity=body.quantity,
                warehouse_location_id=body.warehouse_location_id,
                quarantine_location_id=q_loc,
                inspection_id=qi.id,
                created_by=user_id,
            )
        await session.commit()
    return {"inspection_id": str(qi.id)}


@router.post("/quality/ncr")
async def create_ncr(
    body: NCRCreateRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        ncr = NonConformanceReportModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            inspection_id=body.inspection_id,
            ncr_type=body.ncr_type,
            reason=body.reason,
            action_taken=body.action_taken,
        )
        session.add(ncr)
        await session.commit()
    return {"id": str(ncr.id)}


@router.get("/quality/ncrs")
async def list_ncrs(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = select(NonConformanceReportModel).where(NonConformanceReportModel.tenant_id == tenant_id)
        r = await session.execute(stmt)
        rows = r.scalars().all()
    return [
        {
            "id": str(x.id),
            "inspection_id": str(x.inspection_id) if x.inspection_id else None,
            "ncr_type": x.ncr_type,
            "reason": x.reason,
            "action_taken": x.action_taken,
            "created_at": x.created_at.isoformat() if x.created_at else None,
        }
        for x in rows
    ]


@router.get("/quarantine-stock")
async def quarantine_stock(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Quantities in quarantine status by material and location."""
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(
                StockLevelModel.material_id,
                StockLevelModel.location_id,
                StockLevelModel.quantity,
                MaterialModel.code,
                MaterialModel.name,
                LocationModel.name,
            )
            .join(MaterialModel, MaterialModel.id == StockLevelModel.material_id)
            .join(LocationModel, LocationModel.id == StockLevelModel.location_id)
            .where(
                StockLevelModel.tenant_id == tenant_id,
                StockLevelModel.stock_status == "quarantine",
                StockLevelModel.is_deleted.is_(False),
                StockLevelModel.quantity > 0,
            )
        )
        r = await session.execute(stmt)
        rows = r.all()
    return [
        {
            "material_id": str(m_id),
            "material_code": code,
            "material_name": name,
            "location_id": str(loc_id),
            "location_name": loc_name,
            "quantity": float(qty),
        }
        for m_id, loc_id, qty, code, name, loc_name in rows
    ]


# ── Subcontract ───────────────────────────────────────────────────────────────


@router.post("/subcontract/orders", status_code=status.HTTP_201_CREATED)
async def create_subcontract_order(
    body: SubcontractOrderCreate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        num = SubcontractNumberService(session)
        on = await num.generate(tenant_id)
        o = SubcontractOrderModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            order_number=on,
            supplier_id=body.supplier_id,
            product_id=body.product_id,
            product_type=body.product_type,
            quantity=float(body.quantity),
            status="draft",
        )
        session.add(o)
        await session.commit()
    return {"id": str(o.id), "order_number": on}


@router.get("/subcontract/orders")
async def list_subcontract_orders(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(SubcontractOrderModel)
            .where(
                SubcontractOrderModel.tenant_id == tenant_id,
                SubcontractOrderModel.is_deleted.is_(False),
            )
            .order_by(SubcontractOrderModel.created_at.desc())
        )
        r = await session.execute(stmt)
        rows = r.scalars().all()
    return [
        {
            "id": str(x.id),
            "order_number": x.order_number,
            "supplier_id": str(x.supplier_id),
            "product_id": str(x.product_id),
            "product_type": x.product_type,
            "quantity": float(x.quantity),
            "status": x.status,
        }
        for x in rows
    ]


@router.get("/subcontract/orders/{order_id}")
async def get_subcontract_order(
    order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        o = await session.get(SubcontractOrderModel, order_id)
        if not o or o.tenant_id != tenant_id or o.is_deleted:
            raise HTTPException(status_code=404, detail="Subcontract order not found")
        iss_stmt = select(SubcontractMaterialIssueModel).where(
            SubcontractMaterialIssueModel.subcontract_order_id == order_id,
            SubcontractMaterialIssueModel.tenant_id == tenant_id,
        )
        ir = await session.execute(iss_stmt)
        issues = ir.scalars().all()
    return {
        "id": str(o.id),
        "order_number": o.order_number,
        "supplier_id": str(o.supplier_id),
        "product_id": str(o.product_id),
        "product_type": o.product_type,
        "quantity": float(o.quantity),
        "status": o.status,
        "issues": [
            {
                "id": str(i.id),
                "material_id": str(i.material_id),
                "quantity": float(i.quantity),
                "batch_number": i.batch_number,
                "issued_at": i.issued_at.isoformat() if i.issued_at else None,
            }
            for i in issues
        ],
    }


@router.post("/subcontract/orders/{order_id}/issue")
async def issue_subcontract_material(
    order_id: uuid.UUID,
    body: SubcontractIssueRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        o = await session.get(SubcontractOrderModel, order_id)
        if not o or o.tenant_id != tenant_id or o.is_deleted:
            raise HTTPException(status_code=404, detail="Subcontract order not found")
        sub_loc = await _subcontractor_location(session, tenant_id, o.supplier_id)
        mat = await session.get(MaterialModel, body.material_id)
        inv = InventoryService(session)
        await inv.issue_to_subcontractor(
            tenant_id=tenant_id,
            material_id=body.material_id,
            quantity=body.quantity,
            from_location_id=body.from_location_id,
            subcontractor_location_id=sub_loc,
            subcontract_order_id=o.id,
            unit_id=mat.base_unit_id if mat else None,
            created_by=user_id,
        )
        session.add(
            SubcontractMaterialIssueModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                subcontract_order_id=o.id,
                material_id=body.material_id,
                quantity=float(body.quantity),
                batch_number=body.batch_number,
            )
        )
        o.status = "issued"
        o.updated_at = datetime.now(timezone.utc)
        await session.commit()
    return {"status": "ok"}


@router.post("/subcontract/orders/{order_id}/receive")
async def receive_subcontract(
    order_id: uuid.UUID,
    body: SubcontractReceiveRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        o = await session.get(SubcontractOrderModel, order_id)
        if not o or o.tenant_id != tenant_id or o.is_deleted:
            raise HTTPException(status_code=404, detail="Subcontract order not found")
        mat = await session.get(MaterialModel, body.material_id)
        inv = InventoryService(session)
        await inv.receive_subcontract_finished_goods(
            tenant_id=tenant_id,
            material_id=body.material_id,
            quantity=body.quantity,
            warehouse_location_id=body.warehouse_location_id,
            subcontract_order_id=o.id,
            unit_id=mat.base_unit_id if mat else None,
            created_by=user_id,
        )
        o.status = "received"
        o.updated_at = datetime.now(timezone.utc)
        await session.commit()
    return {"status": "ok"}


# ── Material requests & MRP ───────────────────────────────────────────────────


@router.get("/material-requests")
async def list_material_requests(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = select(MaterialRequestModel).where(
            MaterialRequestModel.tenant_id == tenant_id,
            MaterialRequestModel.is_deleted.is_(False),
        )
        r = await session.execute(stmt)
        rows = r.scalars().all()
    return [
        {
            "id": str(x.id),
            "item_id": str(x.item_id),
            "item_type": x.item_type,
            "required_quantity": float(x.required_quantity),
            "fulfilled_quantity": float(x.fulfilled_quantity),
            "status": x.status,
        }
        for x in rows
    ]


@router.post("/material-requests/run-mrp")
async def run_mrp(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Generate open material_requests where available + incoming - reserved < reorder + safety."""
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = select(MaterialModel).where(
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.is_deleted.is_(False),
            MaterialModel.material_type == "raw",
        )
        r = await session.execute(stmt)
        materials = r.scalars().all()
        inv = InventoryService(session)
        created = 0
        for m in materials:
            rl = m.reorder_level
            if rl is None:
                continue
            rl_d = Decimal(str(rl))
            safety = Decimal(str(m.safety_stock)) if m.safety_stock is not None else Decimal("0")
            avail = await inv._sum_available_internal(tenant_id, m.id)  # noqa: SLF001
            if not await inv._has_stock_levels(tenant_id, m.id):  # noqa: SLF001
                avail = Decimal(str(m.current_stock)) - Decimal(str(m.reserved_stock))
            reserved = Decimal(str(m.reserved_stock))
            q_in = await session.execute(
                select(
                    func.coalesce(
                        func.sum(
                            PurchaseOrderLineModel.quantity - PurchaseOrderLineModel.received_quantity
                        ),
                        0,
                    )
                )
                .join(PurchaseOrderModel, PurchaseOrderModel.id == PurchaseOrderLineModel.purchase_order_id)
                .where(
                    PurchaseOrderLineModel.tenant_id == tenant_id,
                    PurchaseOrderLineModel.material_id == m.id,
                    PurchaseOrderLineModel.is_deleted.is_(False),
                    PurchaseOrderModel.is_deleted.is_(False),
                    PurchaseOrderModel.status.in_(("sent", "acknowledged", "partial")),
                )
            )
            incoming = Decimal(str(q_in.scalar_one()))
            net = avail + incoming - reserved
            need = rl_d + safety - net
            if need > 0:
                mr = MaterialRequestModel(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    item_id=m.id,
                    item_type="material",
                    required_quantity=float(need),
                    fulfilled_quantity=0,
                    status="open",
                    source_ref_type="mrp",
                )
                session.add(mr)
                created += 1
        await session.commit()
    return {"created": created}


# ── Supplier portal ───────────────────────────────────────────────────────────


@router.get("/supplier/purchase-orders")
async def supplier_list_pos(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(
                PurchaseOrderModel.tenant_id == tenant_id,
                PurchaseOrderModel.supplier_id == supplier_id,
                PurchaseOrderModel.is_deleted.is_(False),
            )
        )
        r = await session.execute(stmt)
        pos = r.scalars().unique().all()
    return [
        {
            "id": str(p.id),
            "po_number": p.po_number,
            "status": p.status,
            "total_amount": float(p.total_amount),
        }
        for p in pos
    ]


@router.get("/supplier/purchase-orders/{po_id}")
async def supplier_get_po(
    po_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(
                PurchaseOrderModel.id == po_id,
                PurchaseOrderModel.tenant_id == tenant_id,
                PurchaseOrderModel.supplier_id == supplier_id,
                PurchaseOrderModel.is_deleted.is_(False),
            )
        )
        r = await session.execute(stmt)
        p = r.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="PO not found")
    return _po_to_dict(p)


@router.put("/supplier/purchase-orders/{po_id}/acknowledge")
async def supplier_ack_po(
    po_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        po = await session.get(PurchaseOrderModel, po_id)
        if not po or po.tenant_id != tenant_id or po.is_deleted:
            raise HTTPException(status_code=404, detail="PO not found")
        if po.supplier_id != supplier_id:
            raise HTTPException(status_code=403, detail="Not your purchase order")
        po.status = "acknowledged"
        po.updated_at = datetime.now(timezone.utc)
        await session.commit()
    return {"status": "ok"}


@router.post("/supplier/quotations", status_code=status.HTTP_201_CREATED)
async def supplier_submit_quotation(
    body: SupplierQuotationCreate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        q = SupplierQuotationModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            purchase_order_id=body.purchase_order_id,
            material_id=body.material_id,
            quantity=float(body.quantity),
            unit_price=float(body.unit_price),
            valid_until=body.valid_until,
            status="submitted",
        )
        session.add(q)
        await session.commit()
    return {"id": str(q.id)}


# ── Inspection results query ─────────────────────────────────────────────────


@router.get("/quality/inspections")
async def list_inspections(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = select(QualityInspectionModel).where(QualityInspectionModel.tenant_id == tenant_id)
        r = await session.execute(stmt)
        rows = r.scalars().all()
    return [
        {
            "id": str(x.id),
            "reference_type": x.reference_type,
            "reference_id": str(x.reference_id),
            "result": x.result,
            "inspection_date": x.inspection_date.isoformat(),
        }
        for x in rows
    ]
