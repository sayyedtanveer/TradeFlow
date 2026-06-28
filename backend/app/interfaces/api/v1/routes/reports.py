"""Reporting & Analytics API routes - role-filtered cross-module reports."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.interfaces.api.v1.dependencies.auth import (
    get_current_tenant_id,
    get_current_role,
)
from backend.app.application.finance.reporting_service import ReportingService
from backend.app.application.documents.services.document_generation_service import DocumentGenerationService
from backend.app.application.documents.services.template_service import TemplateService
from backend.app.application.documents.services.pdf_generation_service import PDFGenerationService
from backend.app.application.documents.services.document_storage_service import DocumentStorageService

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])


async def _get_db_session(request: Request):
    factory = request.app.state.container.session_factory
    async with factory() as session:
        yield session


@router.get("/inventory/summary")
async def inventory_summary(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Inventory summary with low-stock flags."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.inventory_summary(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/inventory/turnover")
async def inventory_turnover(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Inventory turnover from materialized view."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.inventory_turnover(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/inventory/near-empty-batches")
async def near_empty_batches(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
    threshold_pct: float = Query(10.0, ge=0, le=100),
):
    """Batches below threshold % of original quantity."""
    from sqlalchemy import select
    from backend.app.infrastructure.persistence.models.batch_model import BatchModel

    rows = (
        await session.execute(
            select(BatchModel).where(
                BatchModel.tenant_id == tenant_id,
                BatchModel.is_deleted.is_(False),
                BatchModel.remaining_quantity.isnot(None),
            )
        )
    ).scalars().all()
    result = []
    for b in rows:
        orig = float(b.original_quantity or b.quantity or 0)
        rem = float(b.remaining_quantity or 0)
        if orig <= 0:
            continue
        pct = rem / orig * 100
        if pct <= threshold_pct:
            result.append({
                "batch_id": str(b.id),
                "batch_number": b.batch_number,
                "material_id": str(b.material_id),
                "remaining_quantity": rem,
                "original_quantity": orig,
                "percent_remaining": round(pct, 2),
            })
    return result


@router.get("/sales/summary")
async def sales_summary(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Sales orders summary — by status + monthly trend."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.sales_summary(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/sales/top-clients")
async def top_clients(
    request: Request,
    limit: int = Query(10, ge=1, le=50),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Top clients by revenue."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.top_clients(tenant_id, role.upper(), limit)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/procurement/summary")
async def procurement_summary(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Procurement summary by PO status."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.procurement_summary(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/summary")
async def finance_summary(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Finance summary — AR + AP."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.finance_summary(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/ar-aging")
async def ar_aging(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Accounts Receivable aging by client."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.ar_aging(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/ap-aging")
async def ap_aging(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Accounts Payable aging by supplier."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.ap_aging(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/trial-balance")
async def trial_balance(
    request: Request,
    as_of: Optional[date] = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Trial balance as of a date."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.trial_balance(tenant_id, role.upper(), as_of=as_of)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/profit-loss")
async def profit_and_loss(
    request: Request,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Profit and loss report."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.profit_and_loss(tenant_id, role.upper(), from_date=from_date, to_date=to_date)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/balance-sheet")
async def balance_sheet(
    request: Request,
    as_of: Optional[date] = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Balance sheet as of a date."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.balance_sheet(tenant_id, role.upper(), as_of=as_of)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/cash-flow")
async def cash_flow(
    request: Request,
    months: int = Query(6, ge=1, le=24),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Cash flow statement."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.cash_flow(tenant_id, role.upper(), months=months)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/refresh-views")
async def refresh_materialized_views(
    view_name: Optional[str] = Query(None),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Manually refresh materialized views (ADMIN only)."""
    if role.upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    svc = ReportingService(session)
    refreshed = await svc.refresh_views(view_name)
    return {"refreshed": refreshed}


@router.get("/inventory/summary/export/pdf")
async def inventory_summary_pdf(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Export inventory summary as PDF."""
    role = request.scope.get("user_role", "viewer")
    try:
        from datetime import datetime
        
        # Get report data
        svc = ReportingService(session)
        data = await svc.inventory_summary(tenant_id, role.upper())
        
        # Get tenant info
        from backend.app.domain.tenant.repositories import TenantRepository
        tenant_repo = TenantRepository(session)
        tenant = await tenant_repo.get_by_id(tenant_id)
        
        # Build template context
        context = {
            "tenant": {
                "name": tenant.name,
                "company_name": tenant.company_name or tenant.name,
                "logo_url": tenant.logo_url or "",
                "gst_number": tenant.gst_number or "",
                "pan_number": tenant.pan_number or "",
                "address": tenant.address or "",
                "phone": tenant.phone or "",
                "email": tenant.email or "",
                "footer_text": tenant.footer_text or "",
            },
            "report": {
                "title": "Inventory Summary Report",
                "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "data": data,
            },
        }
        
        # Generate PDF using simple HTML template
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Inventory Summary</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .low-stock {{ color: red; font-weight: bold; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <h1>{context['tenant']['company_name']}</h1>
            <p>GST: {context['tenant']['gst_number']}</p>
            <p>PAN: {context['tenant']['pan_number']}</p>
            <p>{context['tenant']['address']}</p>
            <h2>Inventory Summary Report</h2>
            <p>Generated: {context['report']['generated_at']}</p>
            <table>
                <tr>
                    <th>Code</th>
                    <th>Name</th>
                    <th>Category</th>
                    <th>On Hand</th>
                    <th>Reserved</th>
                    <th>Available</th>
                    <th>Reorder Level</th>
                </tr>
                {''.join([f'''
                <tr>
                    <td>{row.get('code', '')}</td>
                    <td>{row.get('name', '')}</td>
                    <td>{row.get('category', '')}</td>
                    <td>{row.get('quantity_on_hand', 0)}</td>
                    <td>{row.get('quantity_reserved', 0)}</td>
                    <td>{row.get('available', 0)}</td>
                    <td class="{'low-stock' if row.get('is_low_stock') else ''}">{row.get('reorder_level', 0)}</td>
                </tr>
                ''' for row in data])}
            </table>
            <div class="footer">{context['tenant']['footer_text']}</div>
        </body>
        </html>
        """
        
        # Generate PDF
        pdf_service = PDFGenerationService()
        pdf_content = pdf_service.generate_pdf_from_string(html)
        
        # Store PDF
        storage_service = DocumentStorageService()
        file_path = storage_service.generate_file_path(tenant_id, "inventory_summary", f"inventory_summary_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf")
        storage_service.save_file(file_path, pdf_content)
        
        return {
            "file_path": file_path,
            "download_url": f"/api/v1/documents/download?path={file_path}",
            "generated_at": context['report']['generated_at'],
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/procurement")
async def procurement_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Procurement dashboard with PO status and supplier metrics."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        summary = await svc.procurement_summary(tenant_id, role.upper())
        
        return {
            "purchase_orders": summary,
            "pending_approvals": sum(row.get("count", 0) for row in summary.get("by_status", []) if row.get("status") in ["DRAFT", "PENDING_APPROVAL"]),
            "active_orders": sum(row.get("count", 0) for row in summary.get("by_status", []) if row.get("status") in ["APPROVED", "ORDERED"]),
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/dashboard/finance")
async def finance_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Finance dashboard with AR/AP, cash flow, and profitability metrics."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        summary = await svc.finance_summary(tenant_id, role.upper())
        ar_aging = await svc.ar_aging(tenant_id, role.upper())
        ap_aging = await svc.ap_aging(tenant_id, role.upper())
        
        return {
            "summary": summary,
            "ar_aging": ar_aging,
            "ap_aging": ap_aging,
            "cash_position": summary.get("cash_flow", {}).get("net_cash_flow", 0),
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/dashboard/sales")
async def sales_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Sales dashboard with order status, revenue trends, and top clients."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        summary = await svc.sales_summary(tenant_id, role.upper())
        top_clients = await svc.top_clients(tenant_id, role.upper(), limit=10)
        
        return {
            "orders": summary,
            "top_clients": top_clients,
            "pending_orders": sum(row.get("count", 0) for row in summary.get("by_status", []) if row.get("status") in ["PENDING", "CONFIRMED"]),
            "monthly_revenue": summary.get("monthly", []),
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
