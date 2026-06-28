"""
Role-based dashboard endpoints providing KPI views for each user role.

Dashboards are role-specific and tenant-scoped:
- Admin: System-wide KPIs
- Supplier: Self-only purchase orders and quotations
- Sales: Sales order and client metrics
- Client: Sales order tracking and delivery status
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select, func
from backend.app.infrastructure.persistence.models.purchase_order_model import PurchaseOrderModel
from backend.app.infrastructure.persistence.models.grn_model import GoodsReceiptNoteModel
from backend.app.infrastructure.persistence.models.sales_models import ClientModel, SalesOrderModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.stock_level_model import StockLevelModel as InventoryModel
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from backend.app.infrastructure.persistence.models.user_model import UserModel

from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_role,
    get_current_tenant_id,
    get_current_user_id,
)
from backend.app.application.rbac.service import get_effective_role_permissions
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission

router = APIRouter(tags=["Dashboards"])


@router.get(
    "/dashboards/admin",
    dependencies=[Depends(require_permission("admin:read"))],
)
@router.get(
    "/dashboard/admin",
    dependencies=[Depends(require_permission("admin:read"))],
    include_in_schema=False,
)
async def admin_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """
    Admin system-wide KPI dashboard.
    
    Shows:
    - Purchase order metrics (count by status)
    - GRN reception metrics
    - Inventory levels and alerts
    - Work order status distribution
    - Sales order status distribution
    - Production completion percentage
    """
    container = get_container(request)
    async with container.session_factory() as session:
        # PO metrics
        po_stmt = select(
            PurchaseOrderModel.status,
            func.count(PurchaseOrderModel.id).label("count")
        ).where(
            PurchaseOrderModel.tenant_id == tenant_id,
            PurchaseOrderModel.is_deleted.is_(False),
        ).group_by(PurchaseOrderModel.status)
        
        po_result = await session.execute(po_stmt)
        po_by_status = {row[0]: row[1] for row in po_result}
        total_pos = sum(po_by_status.values())
        
        # GRN metrics
        grn_stmt = select(func.count(GoodsReceiptNoteModel.id)).where(
            GoodsReceiptNoteModel.tenant_id == tenant_id,
            GoodsReceiptNoteModel.is_deleted.is_(False),
        )
        grn_count = (await session.execute(grn_stmt)).scalar() or 0
        
        # Inventory metrics (low stock alerts)
        low_stock_stmt = select(func.count(MaterialModel.id)).where(
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.reorder_level.isnot(None),
            MaterialModel.current_stock <= MaterialModel.reorder_level,
            MaterialModel.is_deleted.is_(False),
        )
        low_stock_count = (await session.execute(low_stock_stmt)).scalar() or 0
        
        # WO metrics
        wo_stmt = select(
            WorkOrderModel.status,
            func.count(WorkOrderModel.id).label("count")
        ).where(
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        ).group_by(WorkOrderModel.status)
        
        wo_result = await session.execute(wo_stmt)
        wo_by_status = {row[0]: row[1] for row in wo_result}
        total_wos = sum(wo_by_status.values())
        
        # SO metrics
        so_stmt = select(
            SalesOrderModel.status,
            func.count(SalesOrderModel.id).label("count")
        ).where(
            SalesOrderModel.tenant_id == tenant_id,
            SalesOrderModel.is_deleted.is_(False),
        ).group_by(SalesOrderModel.status)
        
        so_result = await session.execute(so_stmt)
        so_by_status = {row[0]: row[1] for row in so_result}
        total_sos = sum(so_by_status.values())

        revenue = await session.scalar(
            select(func.coalesce(func.sum(SalesOrderModel.grand_total), 0)).where(
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.status.in_(["DELIVERED", "COMPLETED"]),
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        open_orders = await session.scalar(
            select(func.count(SalesOrderModel.id)).where(
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.status.in_(
                    ["PENDING_APPROVAL", "APPROVED", "CONFIRMED", "PRODUCTION", "READY", "SHIPPED"]
                ),
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        
        # Production completion %
        completed_wos = wo_by_status.get("COMPLETED", 0)
        production_completion_pct = (
            (completed_wos / total_wos * 100) if total_wos > 0 else 0
        )
        
        # Total inventory value (estimated)
        inv_value_stmt = select(
            func.sum(InventoryModel.quantity * MaterialModel.current_cost)
        ).join(
            MaterialModel, InventoryModel.material_id == MaterialModel.id
        ).where(
            MaterialModel.tenant_id == tenant_id,
            InventoryModel.is_deleted.is_(False),
        )
        
        inv_value = (await session.execute(inv_value_stmt)).scalar() or Decimal("0")
    
    return {
        "dashboard_type": "admin",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "purchase_orders": {
            "total": total_pos,
            "by_status": po_by_status,
        },
        "goods_receipts": {
            "total": grn_count,
        },
        "inventory": {
            "low_stock_alerts": low_stock_count,
            "estimated_value": float(inv_value),
        },
        "revenue": float(revenue or 0),
        "open_orders": int(open_orders or 0),
        "open_work_orders": int(total_wos - completed_wos),
        "production_target_progress": round(production_completion_pct, 1),
        "work_orders": {
            "total": total_wos,
            "by_status": wo_by_status,
            "completion_percentage": round(production_completion_pct, 1),
        },
        "sales_orders": {
            "total": total_sos,
            "by_status": so_by_status,
        },
    }


@router.get(
    "/dashboards/supplier",
    dependencies=[Depends(require_permission("supplier:read"))],
)
@router.get(
    "/dashboard/supplier",
    dependencies=[Depends(require_permission("supplier:read"))],
    include_in_schema=False,
)
async def supplier_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Supplier portal dashboard.
    
    Shows:
    - My purchase orders (filtered by supplier_id from JWT)
    - My quotations by status
    - My performance rating
    - Quotes awaiting response
    """
    container = get_container(request)
    async with container.session_factory() as session:
        # Get user's supplier_id
        user = await session.get(UserModel, user_id)
        if not user or user.supplier_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User must be associated with a supplier",
            )
        
        supplier_id = user.supplier_id
        
        # My POs
        po_stmt = select(
            PurchaseOrderModel.status,
            func.count(PurchaseOrderModel.id).label("count")
        ).where(
            PurchaseOrderModel.tenant_id == tenant_id,
            PurchaseOrderModel.supplier_id == supplier_id,
            PurchaseOrderModel.is_deleted.is_(False),
        ).group_by(PurchaseOrderModel.status)
        
        po_result = await session.execute(po_stmt)
        po_by_status = {row[0]: row[1] for row in po_result}
        total_pos = sum(po_by_status.values())
        
        # My quotations
        quotation_stmt = select(
            SupplierQuotationModel.status,
            func.count(SupplierQuotationModel.id).label("count")
        ).where(
            SupplierQuotationModel.tenant_id == tenant_id,
            SupplierQuotationModel.supplier_id == supplier_id,
            SupplierQuotationModel.is_deleted.is_(False),
        ).group_by(SupplierQuotationModel.status)
        
        quotation_result = await session.execute(quotation_stmt)
        quotation_by_status = {row[0]: row[1] for row in quotation_result}
        total_quotations = sum(quotation_by_status.values())
        
        # Pending quotations (DRAFT or SUBMITTED)
        pending_quotations = (
            quotation_by_status.get("DRAFT", 0) +
            quotation_by_status.get("SUBMITTED", 0)
        )
        
        # Supplier performance rating
        supplier = await session.get(SupplierModel, supplier_id)
        supplier_rating = supplier.performance_rating if supplier else None
    
    return {
        "dashboard_type": "supplier",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "purchase_orders": {
            "total": total_pos,
            "by_status": po_by_status,
        },
        "quotations": {
            "total": total_quotations,
            "by_status": quotation_by_status,
            "pending_action": pending_quotations,
        },
        "performance": {
            "rating": supplier_rating,
        },
    }


@router.get(
    "/dashboards/manager",
    dependencies=[Depends(require_permission("sales:approve_order"))],
)
@router.get(
    "/dashboard/manager",
    dependencies=[Depends(require_permission("sales:approve_order"))],
    include_in_schema=False,
)
async def manager_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    role: str = Depends(get_current_role),
):
    """Manager operational workspace dashboard with queue-first design."""
    container = get_container(request)
    async with container.session_factory() as session:
        # Manufacturing manager service removed - return basic dashboard data
        dashboard_data = {
            "dashboard_type": "manager",
            "message": "Manufacturing manager dashboard has been removed in TradeFlow distribution system.",
        }
        
        # Add legacy pending approvals for backward compatibility
        pending_query = select(SalesOrderModel).where(
            SalesOrderModel.tenant_id == tenant_id,
            SalesOrderModel.status == "PENDING_APPROVAL",
            SalesOrderModel.is_deleted.is_(False),
        )
        effective_role = await get_effective_role_permissions(session, tenant_id, role)
        if not effective_role.has_all:
            pending_query = pending_query.where(
                (SalesOrderModel.approver_id == user_id) | (SalesOrderModel.approver_id.is_(None))
            )

        pending_orders = (
            await session.execute(
                pending_query.order_by(SalesOrderModel.submitted_at.asc()).limit(25)
            )
        ).scalars().all()

        dashboard_data["legacy_pending_approvals"] = {
            "count": len(pending_orders),
            "items": [
                {
                    "id": str(order.id),
                    "order_number": order.order_number,
                    "client_id": str(order.client_id),
                    "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                    "grand_total": float(order.grand_total or 0),
                }
                for order in pending_orders
            ],
        }

    return dashboard_data


@router.get(
    "/dashboards/sales",
    dependencies=[Depends(require_permission("sales:read"))],
)
@router.get(
    "/dashboard/sales",
    dependencies=[Depends(require_permission("sales:read"))],
    include_in_schema=False,
)
async def sales_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Sales dashboard with approvals, monthly sales value, and top clients."""
    container = get_container(request)
    since = datetime.now(timezone.utc) - timedelta(days=30)
    async with container.session_factory() as session:
        pending_approvals = await session.scalar(
            select(func.count(SalesOrderModel.id)).where(
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.status == "PENDING_APPROVAL",
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        monthly_sales = await session.scalar(
            select(func.coalesce(func.sum(SalesOrderModel.grand_total), 0)).where(
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.status.in_(["APPROVED", "CONFIRMED", "READY", "SHIPPED", "DELIVERED", "COMPLETED"]),
                SalesOrderModel.created_at >= since,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        top_result = await session.execute(
            select(
                ClientModel.id,
                ClientModel.name,
                func.coalesce(func.sum(SalesOrderModel.grand_total), 0).label("sales_value"),
            )
            .join(SalesOrderModel, SalesOrderModel.client_id == ClientModel.id)
            .where(
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.is_deleted.is_(False),
            )
            .group_by(ClientModel.id, ClientModel.name)
            .order_by(func.coalesce(func.sum(SalesOrderModel.grand_total), 0).desc())
            .limit(10)
        )

    return {
        "dashboard_type": "sales",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pending_approvals": int(pending_approvals or 0),
        "monthly_sales": float(monthly_sales or 0),
        "top_clients": [
            {"client_id": str(row[0]), "name": row[1], "sales_value": float(row[2] or 0)}
            for row in top_result
        ],
    }


@router.get(
    "/dashboards/client",
    dependencies=[Depends(require_permission("client:read"))],
)
@router.get(
    "/dashboard/client",
    dependencies=[Depends(require_permission("client:read"))],
    include_in_schema=False,
)
async def client_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Client sales order dashboard.
    
    Shows:
    - Sales orders by status
    - Pending delivery
    - Shipment tracking
    - Order history
    """
    container = get_container(request)
    async with container.session_factory() as session:
        user = await session.get(UserModel, user_id)
        client_filter = []
        if user and user.client_id:
            client_filter.append(SalesOrderModel.client_id == user.client_id)

        # SO metrics
        so_stmt = select(
            SalesOrderModel.status,
            func.count(SalesOrderModel.id).label("count")
        ).where(
            SalesOrderModel.tenant_id == tenant_id,
            SalesOrderModel.is_deleted.is_(False),
            *client_filter,
        ).group_by(SalesOrderModel.status)
        
        so_result = await session.execute(so_stmt)
        so_by_status = {row[0]: row[1] for row in so_result}
        
        # Pending delivery once stock or production is ready.
        pending_delivery = so_by_status.get("CONFIRMED", 0) + so_by_status.get("READY", 0)
        
        # Shipped
        shipped = so_by_status.get("SHIPPED", 0)
        
        # Recent SOs (last 5)
        recent_sos_stmt = select(
            SalesOrderModel.id,
            SalesOrderModel.order_number,
            SalesOrderModel.status,
            SalesOrderModel.order_date,
            SalesOrderModel.delivery_date,
        ).where(
            SalesOrderModel.tenant_id == tenant_id,
            SalesOrderModel.is_deleted.is_(False),
            *client_filter,
        ).order_by(
            SalesOrderModel.created_at.desc()
        ).limit(5)
        
        recent_result = await session.execute(recent_sos_stmt)
        recent_sos = [
            {
                "so_id": str(row[0]),
                "so_number": row[1],
                "status": row[2],
                "order_date": str(row[3]) if row[3] else None,
                "expected_delivery": str(row[4]) if row[4] else None,
            }
            for row in recent_result
        ]
    
    return {
        "dashboard_type": "client",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sales_orders": so_by_status,
        "pending_delivery": pending_delivery,
        "shipped": shipped,
        "recent_orders": recent_sos,
    }
