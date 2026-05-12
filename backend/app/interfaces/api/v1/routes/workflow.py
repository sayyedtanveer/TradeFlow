"""Workflow Orchestration REST API endpoints.

Provides endpoints for end-to-end workflow management across modules.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Dict, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_current_user_id
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.application.manufacturing.services.workflow_orchestration_service import (
    WorkflowOrchestrationService,
)

router = APIRouter(prefix="/workflow", tags=["Workflow Orchestration"])


async def _get_db_session(request):
    """Get database session from request."""
    factory = request.app.state.container.session_factory
    async with factory() as session:
        yield session


@router.post(
    "/sales-orders/{sales_order_id}/approve-workflow",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("sales:approve_order"))],
)
async def approve_sales_order_workflow(
    sales_order_id: uuid.UUID,
    request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """
    Approve Sales Order and trigger workflow.
    
    Transition: APPROVED → WORK_ORDER_CREATED
    Action: Create Work Orders for each line item
    """
    service = WorkflowOrchestrationService(session)
    result = await service.on_sales_order_approved(
        tenant_id=tenant_id,
        sales_order_id=sales_order_id,
    )
    await session.commit()
    return result


@router.post(
    "/work-orders/{work_order_id}/complete-workflow",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("manufacturing:write"))],
)
async def complete_work_order_workflow(
    work_order_id: uuid.UUID,
    request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """
    Complete Work Order and trigger workflow.
    
    Transition: FG_RECEIVED → READY_FOR_DISPATCH
    Action: Update linked Sales Order to READY_FOR_DISPATCH
    """
    service = WorkflowOrchestrationService(session)
    result = await service.on_work_order_completed(
        tenant_id=tenant_id,
        work_order_id=work_order_id,
    )
    await session.commit()
    return result


@router.post(
    "/work-orders/{work_order_id}/qc-approve-workflow",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("quality:write"))],
)
async def qc_approve_workflow(
    work_order_id: uuid.UUID,
    request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    approved_by: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """
    Approve QC and trigger workflow.
    
    Transition: QC_APPROVED → FG_RECEIVED
    Action: Automatically increase FG stock
    """
    service = WorkflowOrchestrationService(session)
    result = await service.on_qc_approved(
        tenant_id=tenant_id,
        work_order_id=work_order_id,
        received_by=approved_by,
    )
    await session.commit()
    return result


@router.post(
    "/sales-orders/{sales_order_id}/deliver-workflow",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("sales:write"))],
)
async def deliver_order_workflow(
    sales_order_id: uuid.UUID,
    request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """
    Mark Order as delivered and trigger invoicing.
    
    Transition: DELIVERED → INVOICED
    Action: Trigger invoice creation
    """
    service = WorkflowOrchestrationService(session)
    result = await service.on_order_delivered(
        tenant_id=tenant_id,
        sales_order_id=sales_order_id,
    )
    await session.commit()
    return result


@router.post(
    "/sales-orders/{sales_order_id}/payment-workflow",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("finance:write"))],
)
async def receive_payment_workflow(
    sales_order_id: uuid.UUID,
    payment_amount: Decimal,
    request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """
    Record payment and complete workflow.
    
    Transition: INVOICED → PAYMENT_RECEIVED → COMPLETED
    Action: Update Sales Order status
    """
    service = WorkflowOrchestrationService(session)
    result = await service.on_payment_received(
        tenant_id=tenant_id,
        sales_order_id=sales_order_id,
        payment_amount=payment_amount,
    )
    await session.commit()
    return result


@router.get(
    "/sales-orders/{sales_order_id}/status",
    dependencies=[Depends(require_permission("sales:read"))],
)
async def get_workflow_status(
    sales_order_id: uuid.UUID,
    request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """
    Get complete workflow status for a Sales Order.
    
    Returns status across all stages:
    - Sales Order status
    - Work Order status
    - Material reservation status
    - QC status
    - Delivery status
    - Invoice status
    - Payment status
    """
    service = WorkflowOrchestrationService(session)
    result = await service.get_workflow_status(
        tenant_id=tenant_id,
        sales_order_id=sales_order_id,
    )
    return result
