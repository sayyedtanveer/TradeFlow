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

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])


async def _get_db_session(request: Request):
    factory = request.app.state.container.session_factory
    async with factory() as session:
        yield session


@router.get("/inventory/summary")
async def inventory_summary(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Inventory summary with low-stock flags."""
    try:
        svc = ReportingService(session)
        return await svc.inventory_summary(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/inventory/turnover")
async def inventory_turnover(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Inventory turnover from materialized view."""
    try:
        svc = ReportingService(session)
        return await svc.inventory_turnover(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/production/summary")
async def production_summary(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Work order summary by status."""
    try:
        svc = ReportingService(session)
        return await svc.work_order_summary(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/production/efficiency")
async def production_efficiency(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Work order efficiency — scrap rates by month."""
    try:
        svc = ReportingService(session)
        return await svc.work_order_efficiency(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/sales/summary")
async def sales_summary(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Sales orders summary — by status + monthly trend."""
    try:
        svc = ReportingService(session)
        return await svc.sales_summary(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/sales/top-clients")
async def top_clients(
    limit: int = Query(10, ge=1, le=50),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Top clients by revenue."""
    try:
        svc = ReportingService(session)
        return await svc.top_clients(tenant_id, role.upper(), limit)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/procurement/summary")
async def procurement_summary(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Procurement summary by PO status."""
    try:
        svc = ReportingService(session)
        return await svc.procurement_summary(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/quality/summary")
async def quality_summary(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Quality inspection results summary."""
    try:
        svc = ReportingService(session)
        return await svc.quality_summary(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/summary")
async def finance_summary(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Finance summary — AR + AP."""
    try:
        svc = ReportingService(session)
        return await svc.finance_summary(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/ar-aging")
async def ar_aging(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Accounts Receivable aging by client."""
    try:
        svc = ReportingService(session)
        return await svc.ar_aging(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/ap-aging")
async def ap_aging(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Accounts Payable aging by supplier."""
    try:
        svc = ReportingService(session)
        return await svc.ap_aging(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/trial-balance")
async def trial_balance(
    as_of: Optional[date] = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Trial balance as of a date."""
    try:
        svc = ReportingService(session)
        return await svc.trial_balance(tenant_id, role.upper(), as_of=as_of)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/profit-loss")
async def profit_and_loss(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Profit and loss report."""
    try:
        svc = ReportingService(session)
        return await svc.profit_and_loss(tenant_id, role.upper(), from_date=from_date, to_date=to_date)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/balance-sheet")
async def balance_sheet(
    as_of: Optional[date] = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Balance sheet as of a date."""
    try:
        svc = ReportingService(session)
        return await svc.balance_sheet(tenant_id, role.upper(), as_of=as_of)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/cash-flow")
async def cash_flow(
    months: int = Query(6, ge=1, le=24),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Cash flow statement."""
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
