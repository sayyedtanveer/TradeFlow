"""Finance API routes — Invoice, Payment, Supplier Invoice, AP/AR."""

from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.interfaces.api.v1.dependencies.auth import (
    get_current_user_id,
    get_current_tenant_id,
    get_current_role,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.infrastructure.persistence.database import get_db
from backend.app.application.finance.finance_service import FinanceService
from backend.app.application.finance.notification_service import NotificationService

router = APIRouter(prefix="/finance", tags=["Finance"])


# ── Permission Guards ───────────────────────────────────────────────────
FINANCE_ROLES = ["ADMIN", "ACCOUNTANT", "MANAGER"]
SALES_VIEW_ROLES = FINANCE_ROLES + ["SALES", "VIEWER"]


def _require_finance(role: str = Depends(get_current_role)):
    if role.upper() not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Finance access required (ADMIN/ACCOUNTANT/MANAGER)")


def _get_session(request: Request):
    return request.app.state.container.session_factory


async def _get_db_session(request: Request):
    factory = request.app.state.container.session_factory
    async with factory() as session:
        yield session


# ── Schemas ──────────────────────────────────────────────────────────────

class InvoiceLineCreate(BaseModel):
    product_id: uuid.UUID
    product_type: str = "finished"
    description: Optional[str] = None
    quantity: int = Field(gt=0)
    unit_price: float = Field(gt=0)
    discount_amount: float = 0
    tax_rate: float = 0
    tax_amount: float = 0
    total: float


class InvoiceCreateFromSO(BaseModel):
    sales_order_id: uuid.UUID
    notes: Optional[str] = None
    terms: Optional[str] = None


class InvoiceCreateManual(BaseModel):
    client_id: uuid.UUID
    invoice_date: date
    due_date: date
    lines: List[InvoiceLineCreate]
    notes: Optional[str] = None
    terms: Optional[str] = None


class PaymentCreate(BaseModel):
    invoice_id: uuid.UUID
    amount: float = Field(gt=0)
    payment_date: date
    payment_method: str = "BANK_TRANSFER"
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class SupplierInvoiceCreate(BaseModel):
    supplier_id: uuid.UUID
    purchase_order_id: Optional[uuid.UUID] = None
    supplier_invoice_ref: Optional[str] = None
    invoice_date: date
    due_date: date
    subtotal: float
    tax_amount: float = 0
    grand_total: float
    notes: Optional[str] = None


class SupplierPaymentCreate(BaseModel):
    supplier_invoice_id: uuid.UUID
    amount: float = Field(gt=0)
    payment_date: date
    payment_method: str = "BANK_TRANSFER"
    reference_number: Optional[str] = None
    notes: Optional[str] = None


def _serialize_invoice(inv) -> dict:
    return {
        "id": str(inv.id),
        "invoice_number": inv.invoice_number,
        "sales_order_id": str(inv.sales_order_id) if inv.sales_order_id else None,
        "client_id": str(inv.client_id),
        "client_name": inv.client_name,
        "client_address": inv.client_address,
        "client_gst_number": inv.client_gst_number,
        "status": inv.status,
        "invoice_date": str(inv.invoice_date),
        "due_date": str(inv.due_date),
        "subtotal": float(inv.subtotal),
        "discount_amount": float(inv.discount_amount),
        "tax_amount": float(inv.tax_amount),
        "grand_total": float(inv.grand_total),
        "paid_amount": float(inv.paid_amount),
        "balance_due": float(inv.grand_total) - float(inv.paid_amount),
        "notes": inv.notes,
        "terms": inv.terms,
        "created_at": inv.created_at.isoformat(),
        "lines": [_serialize_line(l) for l in (inv.lines or [])],
        "payments": [_serialize_payment_brief(p) for p in (inv.payments or [])],
    }


def _serialize_line(l) -> dict:
    return {
        "id": str(l.id),
        "product_id": str(l.product_id),
        "product_type": l.product_type,
        "description": l.description,
        "quantity": l.quantity,
        "unit_price": float(l.unit_price),
        "discount_amount": float(l.discount_amount),
        "tax_rate": float(l.tax_rate),
        "tax_amount": float(l.tax_amount),
        "total": float(l.total),
    }


def _serialize_payment_brief(p) -> dict:
    return {
        "id": str(p.id),
        "payment_number": p.payment_number,
        "amount": float(p.amount),
        "payment_date": str(p.payment_date),
        "payment_method": p.payment_method,
    }


def _serialize_payment(p) -> dict:
    return {
        "id": str(p.id),
        "payment_number": p.payment_number,
        "invoice_id": str(p.invoice_id),
        "client_id": str(p.client_id),
        "amount": float(p.amount),
        "payment_date": str(p.payment_date),
        "payment_method": p.payment_method,
        "reference_number": p.reference_number,
        "notes": p.notes,
        "created_at": p.created_at.isoformat(),
    }


def _serialize_supplier_invoice(si) -> dict:
    return {
        "id": str(si.id),
        "invoice_number": si.invoice_number,
        "supplier_invoice_ref": si.supplier_invoice_ref,
        "purchase_order_id": str(si.purchase_order_id) if si.purchase_order_id else None,
        "supplier_id": str(si.supplier_id),
        "supplier_name": si.supplier_name,
        "status": si.status,
        "invoice_date": str(si.invoice_date),
        "due_date": str(si.due_date),
        "subtotal": float(si.subtotal),
        "tax_amount": float(si.tax_amount),
        "grand_total": float(si.grand_total),
        "paid_amount": float(si.paid_amount),
        "balance_due": float(si.grand_total) - float(si.paid_amount),
        "notes": si.notes,
        "created_at": si.created_at.isoformat(),
    }


# ── Invoice Endpoints ──────────────────────────────────────────────────

@router.post("/invoices/from-so", status_code=status.HTTP_201_CREATED)
async def create_invoice_from_so(
    body: InvoiceCreateFromSO,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Create invoice by snapshotting a delivered sales order."""
    if role.upper() not in FINANCE_ROLES + ["SALES"]:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        svc = FinanceService(session)
        invoice = await svc.create_invoice_from_sales_order(
            tenant_id=tenant_id,
            sales_order_id=body.sales_order_id,
            created_by=user_id,
            notes=body.notes,
            terms=body.terms,
        )
        return _serialize_invoice(invoice)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invoices", status_code=status.HTTP_201_CREATED)
async def create_invoice_manual(
    body: InvoiceCreateManual,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Create a manual invoice not tied to a sales order."""
    if role.upper() not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Finance access required")
    try:
        svc = FinanceService(session)
        invoice = await svc.create_invoice_manual(
            tenant_id=tenant_id,
            client_id=body.client_id,
            invoice_date=body.invoice_date,
            due_date=body.due_date,
            lines_data=[l.model_dump() for l in body.lines],
            created_by=user_id,
            notes=body.notes,
            terms=body.terms,
        )
        return _serialize_invoice(invoice)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invoices")
async def list_invoices(
    status: Optional[str] = Query(None),
    client_id: Optional[uuid.UUID] = Query(None),
    overdue_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in SALES_VIEW_ROLES:
        raise HTTPException(status_code=403, detail="Access denied")
    svc = FinanceService(session)
    result = await svc.list_invoices(
        tenant_id=tenant_id,
        status=status,
        client_id=client_id,
        overdue_only=overdue_only,
        page=page,
        page_size=page_size,
    )
    return {
        **result,
        "items": [_serialize_invoice(i) for i in result["items"]],
    }


@router.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in SALES_VIEW_ROLES + ["CLIENT"]:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        svc = FinanceService(session)
        invoice = await svc.get_invoice(tenant_id, invoice_id)
        return _serialize_invoice(invoice)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/invoices/{invoice_id}/send")
async def send_invoice(
    invoice_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Finance access required")
    try:
        svc = FinanceService(session)
        invoice = await svc.send_invoice(tenant_id, invoice_id)
        return _serialize_invoice(invoice)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invoices/{invoice_id}/void")
async def void_invoice(
    invoice_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in ["ADMIN", "ACCOUNTANT"]:
        raise HTTPException(status_code=403, detail="Admin/Accountant required to void invoice")
    try:
        svc = FinanceService(session)
        invoice = await svc.void_invoice(tenant_id, invoice_id)
        return _serialize_invoice(invoice)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Payment Endpoints ──────────────────────────────────────────────────

@router.post("/payments", status_code=status.HTTP_201_CREATED)
async def record_payment(
    body: PaymentCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Finance access required")
    try:
        svc = FinanceService(session)
        payment = await svc.record_payment(
            tenant_id=tenant_id,
            invoice_id=body.invoice_id,
            amount=body.amount,
            payment_date=body.payment_date,
            payment_method=body.payment_method,
            created_by=user_id,
            reference_number=body.reference_number,
            notes=body.notes,
        )
        return _serialize_payment(payment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/payments")
async def list_payments(
    invoice_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Finance access required")
    svc = FinanceService(session)
    result = await svc.list_payments(tenant_id, invoice_id, page, page_size)
    return {**result, "items": [_serialize_payment(p) for p in result["items"]]}


# ── Supplier Invoice Endpoints ────────────────────────────────────────

@router.post("/supplier-invoices", status_code=status.HTTP_201_CREATED)
async def create_supplier_invoice(
    body: SupplierInvoiceCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Finance access required")
    try:
        svc = FinanceService(session)
        si = await svc.create_supplier_invoice(
            tenant_id=tenant_id,
            supplier_id=body.supplier_id,
            purchase_order_id=body.purchase_order_id,
            supplier_invoice_ref=body.supplier_invoice_ref,
            invoice_date=body.invoice_date,
            due_date=body.due_date,
            subtotal=body.subtotal,
            tax_amount=body.tax_amount,
            grand_total=body.grand_total,
            created_by=user_id,
            notes=body.notes,
        )
        return _serialize_supplier_invoice(si)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/supplier-invoices")
async def list_supplier_invoices(
    status: Optional[str] = Query(None),
    supplier_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Finance access required")
    svc = FinanceService(session)
    result = await svc.list_supplier_invoices(tenant_id, status, supplier_id, page, page_size)
    return {**result, "items": [_serialize_supplier_invoice(si) for si in result["items"]]}


@router.post("/supplier-payments", status_code=status.HTTP_201_CREATED)
async def record_supplier_payment(
    body: SupplierPaymentCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Finance access required")
    try:
        svc = FinanceService(session)
        payment = await svc.record_supplier_payment(
            tenant_id=tenant_id,
            supplier_invoice_id=body.supplier_invoice_id,
            amount=body.amount,
            payment_date=body.payment_date,
            payment_method=body.payment_method,
            created_by=user_id,
            reference_number=body.reference_number,
            notes=body.notes,
        )
        return {
            "id": str(payment.id),
            "payment_number": payment.payment_number,
            "amount": float(payment.amount),
            "payment_date": str(payment.payment_date),
            "payment_method": payment.payment_method,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Dashboard / Analytics Endpoints ─────────────────────────────────

@router.get("/dashboard")
async def finance_dashboard(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Finance dashboard — AR + AP summary."""
    if role.upper() not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Finance access required")
    svc = FinanceService(session)
    ar = await svc.get_ar_summary(tenant_id)
    ap = await svc.get_ap_summary(tenant_id)
    revenue = await svc.get_revenue_by_month(tenant_id, months=6)
    return {"ar": ar, "ap": ap, "revenue_trend": revenue}


@router.get("/ar-aging")
async def ar_aging_report(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Finance access required")
    from backend.app.application.finance.reporting_service import ReportingService
    reporting = ReportingService(session)
    return await reporting.ar_aging(tenant_id, role.upper())


@router.get("/ledger")
async def get_ledger(
    reference_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Full ledger view — admin/accountant only."""
    if role.upper() not in ["ADMIN", "ACCOUNTANT"]:
        raise HTTPException(status_code=403, detail="Admin/Accountant access required")
    svc = FinanceService(session)
    result = await svc.get_ledger(tenant_id, reference_type, page, page_size)
    return {
        **result,
        "items": [
            {
                "id": str(t.id),
                "reference_type": t.reference_type,
                "reference_id": str(t.reference_id),
                "account_type": t.account_type,
                "debit": float(t.debit),
                "credit": float(t.credit),
                "description": t.description,
                "created_at": t.created_at.isoformat(),
            }
            for t in result["items"]
        ],
    }
