"""Reporting service — aggregated queries using materialized views."""

from __future__ import annotations

import uuid
from typing import Optional, List, Dict, Any

from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.finance_models import InvoiceModel
from backend.app.infrastructure.persistence.models.sales_models import SalesOrderModel


ROLE_REPORT_ACCESS = {
    "ADMIN": ["inventory", "production", "sales", "procurement", "quality", "finance", "mrp"],
    "MANAGER": ["inventory", "production", "sales", "procurement", "quality", "finance", "mrp"],
    "ACCOUNTANT": ["finance", "sales"],
    "SALES": ["sales"],
    "QC": ["quality"],
    "OPERATOR": ["production", "inventory"],
    "VIEWER": ["sales", "inventory"],
    "CLIENT": [],
    "SUPPLIER": [],
}


class ReportingService:
    """
    Reporting service — uses materialized views for performance.
    All queries are role-filtered.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def _check_access(self, role: str, report_type: str) -> None:
        allowed = ROLE_REPORT_ACCESS.get(role, [])
        if report_type not in allowed:
            raise PermissionError(f"Role '{role}' cannot access '{report_type}' reports")

    # ------------------------------------------------------------------ #
    #  Inventory Reports
    # ------------------------------------------------------------------ #
    async def inventory_summary(self, tenant_id: uuid.UUID, role: str) -> List[Dict]:
        self._check_access(role, "inventory")
        result = await self.session.execute(
            text("""
                SELECT
                    m.id,
                    m.name,
                    m.code,
                    mc.name as category,
                    sl.quantity_on_hand,
                    sl.quantity_reserved,
                    sl.quantity_on_hand - sl.quantity_reserved as available,
                    m.reorder_level,
                    CASE WHEN sl.quantity_on_hand <= m.reorder_level THEN true ELSE false END as is_low_stock
                FROM materials m
                LEFT JOIN stock_levels sl ON sl.material_id = m.id AND sl.tenant_id = m.tenant_id
                LEFT JOIN material_categories mc ON mc.id = m.category_id
                WHERE m.tenant_id = :tenant_id AND m.is_deleted = false
                ORDER BY m.name
            """),
            {"tenant_id": tenant_id}
        )
        return [dict(row._mapping) for row in result]

    async def inventory_turnover(self, tenant_id: uuid.UUID, role: str) -> List[Dict]:
        self._check_access(role, "inventory")
        try:
            result = await self.session.execute(
                text("""
                    SELECT
                        mvit.material_id,
                        m.name,
                        m.code,
                        mvit.total_consumed,
                        mvit.months_count,
                        CASE WHEN mvit.months_count > 0
                            THEN ROUND(mvit.total_consumed::numeric / mvit.months_count, 2)
                            ELSE 0
                        END as avg_monthly_consumption
                    FROM mv_inventory_turnover mvit
                    LEFT JOIN materials m ON m.id = mvit.material_id
                    WHERE mvit.tenant_id = :tenant_id
                    ORDER BY mvit.total_consumed DESC
                """),
                {"tenant_id": tenant_id}
            )
            return [dict(row._mapping) for row in result]
        except Exception:
            return []

    # ------------------------------------------------------------------ #
    #  Production / Work Order Reports
    # ------------------------------------------------------------------ #
    async def work_order_summary(self, tenant_id: uuid.UUID, role: str) -> Dict:
        self._check_access(role, "production")
        result = await self.session.execute(
            text("""
                SELECT
                    status,
                    COUNT(*) as count,
                    SUM(produced_quantity) as total_produced,
                    SUM(scrap_quantity) as total_scrap
                FROM work_orders
                WHERE tenant_id = :tenant_id
                GROUP BY status
                ORDER BY status
            """),
            {"tenant_id": tenant_id}
        )
        rows = [dict(row._mapping) for row in result]
        return {"by_status": rows}

    async def work_order_efficiency(self, tenant_id: uuid.UUID, role: str) -> List[Dict]:
        self._check_access(role, "production")
        try:
            result = await self.session.execute(
                text("""
                    SELECT month, total_produced, total_scrap, scrap_percentage
                    FROM mv_work_order_efficiency
                    WHERE tenant_id = :tenant_id
                    ORDER BY month DESC
                    LIMIT 12
                """),
                {"tenant_id": tenant_id}
            )
            return [dict(row._mapping) for row in result]
        except Exception:
            return []

    # ------------------------------------------------------------------ #
    #  Sales Reports
    # ------------------------------------------------------------------ #
    async def sales_summary(self, tenant_id: uuid.UUID, role: str) -> Dict:
        self._check_access(role, "sales")
        result = await self.session.execute(
            text("""
                SELECT
                    status,
                    COUNT(*) as count,
                    SUM(grand_total) as total_value
                FROM sales_orders
                WHERE tenant_id = :tenant_id AND is_deleted = false
                GROUP BY status
                ORDER BY status
            """),
            {"tenant_id": tenant_id}
        )
        by_status = [dict(row._mapping) for row in result]

        monthly_result = await self.session.execute(
            text("""
                SELECT
                    date_trunc('month', created_at)::date as month,
                    COUNT(*) as orders,
                    SUM(grand_total) as revenue
                FROM sales_orders
                WHERE tenant_id = :tenant_id AND is_deleted = false
                    AND created_at >= NOW() - INTERVAL '6 months'
                GROUP BY date_trunc('month', created_at)
                ORDER BY month
            """),
            {"tenant_id": tenant_id}
        )
        monthly = [dict(row._mapping) for row in monthly_result]
        return {"by_status": by_status, "monthly": monthly}

    async def top_clients(self, tenant_id: uuid.UUID, role: str, limit: int = 10) -> List[Dict]:
        self._check_access(role, "sales")
        result = await self.session.execute(
            text("""
                SELECT
                    sc.id,
                    sc.name,
                    sc.code,
                    COUNT(so.id) as order_count,
                    SUM(so.grand_total) as total_revenue
                FROM sales_clients sc
                LEFT JOIN sales_orders so ON so.client_id = sc.id AND so.is_deleted = false
                WHERE sc.tenant_id = :tenant_id AND sc.is_deleted = false
                GROUP BY sc.id, sc.name, sc.code
                ORDER BY total_revenue DESC NULLS LAST
                LIMIT :limit
            """),
            {"tenant_id": tenant_id, "limit": limit}
        )
        return [dict(row._mapping) for row in result]

    # ------------------------------------------------------------------ #
    #  Procurement Reports
    # ------------------------------------------------------------------ #
    async def procurement_summary(self, tenant_id: uuid.UUID, role: str) -> Dict:
        self._check_access(role, "procurement")
        result = await self.session.execute(
            text("""
                SELECT
                    status,
                    COUNT(*) as count,
                    SUM(total_amount) as total_value
                FROM purchase_orders
                WHERE tenant_id = :tenant_id AND is_deleted = false
                GROUP BY status
                ORDER BY status
            """),
            {"tenant_id": tenant_id}
        )
        by_status = [dict(row._mapping) for row in result]
        return {"by_status": by_status}

    # ------------------------------------------------------------------ #
    #  Quality Reports
    # ------------------------------------------------------------------ #
    async def quality_summary(self, tenant_id: uuid.UUID, role: str) -> Dict:
        self._check_access(role, "quality")
        result = await self.session.execute(
            text("""
                SELECT
                    result,
                    COUNT(*) as count
                FROM quality_inspections
                WHERE tenant_id = :tenant_id
                GROUP BY result
                ORDER BY result
            """),
            {"tenant_id": tenant_id}
        )
        by_result = [dict(row._mapping) for row in result]
        return {"by_result": by_result}

    # ------------------------------------------------------------------ #
    #  Finance Reports
    # ------------------------------------------------------------------ #
    async def finance_summary(self, tenant_id: uuid.UUID, role: str) -> Dict:
        self._check_access(role, "finance")
        ar = await self.session.execute(
            text("""
                SELECT
                    COUNT(*) as total_invoices,
                    SUM(grand_total) as total_billed,
                    SUM(paid_amount) as total_collected,
                    SUM(grand_total - paid_amount) as outstanding,
                    COUNT(*) FILTER (WHERE status = 'OVERDUE') as overdue_count,
                    SUM(grand_total - paid_amount) FILTER (WHERE status = 'OVERDUE') as overdue_amount
                FROM invoices
                WHERE tenant_id = :tenant_id AND is_deleted = false
            """),
            {"tenant_id": tenant_id}
        )
        ar_row = ar.one()

        ap = await self.session.execute(
            text("""
                SELECT
                    COUNT(*) as total_supplier_invoices,
                    SUM(grand_total) as total_payable,
                    SUM(paid_amount) as total_paid,
                    SUM(grand_total - paid_amount) as outstanding
                FROM supplier_invoices
                WHERE tenant_id = :tenant_id AND is_deleted = false
            """),
            {"tenant_id": tenant_id}
        )
        ap_row = ap.one()

        return {
            "ar": {
                "total_invoices": ar_row.total_invoices,
                "total_billed": float(ar_row.total_billed or 0),
                "total_collected": float(ar_row.total_collected or 0),
                "outstanding": float(ar_row.outstanding or 0),
                "overdue_count": ar_row.overdue_count,
                "overdue_amount": float(ar_row.overdue_amount or 0),
            },
            "ap": {
                "total_supplier_invoices": ap_row.total_supplier_invoices,
                "total_payable": float(ap_row.total_payable or 0),
                "total_paid": float(ap_row.total_paid or 0),
                "outstanding": float(ap_row.outstanding or 0),
            }
        }

    async def ar_aging(self, tenant_id: uuid.UUID, role: str) -> List[Dict]:
        """AR Aging report by client."""
        self._check_access(role, "finance")
        from datetime import date
        today = date.today()
        result = await self.session.execute(
            text("""
                SELECT
                    client_id,
                    client_name,
                    SUM(grand_total - paid_amount) FILTER (
                        WHERE due_date >= :today) as current_amount,
                    SUM(grand_total - paid_amount) FILTER (
                        WHERE due_date < :today AND due_date >= :d30) as overdue_1_30,
                    SUM(grand_total - paid_amount) FILTER (
                        WHERE due_date < :d30 AND due_date >= :d60) as overdue_31_60,
                    SUM(grand_total - paid_amount) FILTER (
                        WHERE due_date < :d60) as overdue_60_plus,
                    SUM(grand_total - paid_amount) as total_outstanding
                FROM invoices
                WHERE tenant_id = :tenant_id
                    AND status NOT IN ('PAID','CANCELLED','VOID')
                    AND is_deleted = false
                GROUP BY client_id, client_name
                ORDER BY total_outstanding DESC
            """),
            {
                "tenant_id": tenant_id,
                "today": today,
                "d30": date(today.year, today.month, today.day - 30 if today.day > 30 else 1),
                "d60": date(today.year, today.month, today.day - 60 if today.day > 60 else 1),
            }
        )
        return [dict(row._mapping) for row in result]

    # ------------------------------------------------------------------ #
    #  Refresh materialized views
    # ------------------------------------------------------------------ #
    async def refresh_views(self, view_name: Optional[str] = None) -> List[str]:
        """Refresh materialized views (called by background job)."""
        views = [
            "mv_inventory_turnover",
            "mv_work_order_efficiency",
            "mv_sales_revenue",
            "mv_ar_aging",
        ]
        if view_name:
            views = [v for v in views if v == view_name]

        refreshed = []
        for view in views:
            try:
                await self.session.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}"))
                refreshed.append(view)
            except Exception as e:
                # Non-fatal — view may not exist or no unique index
                try:
                    await self.session.execute(text(f"REFRESH MATERIALIZED VIEW {view}"))
                    refreshed.append(view)
                except Exception:
                    pass
        await self.session.commit()
        return refreshed
