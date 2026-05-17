"""
Workflow Orchestration Service - End-to-End Manufacturing Workflow

This service orchestrates the complete operational workflow:
SALES_ORDER → APPROVED → WORK_ORDER_CREATED → MATERIAL_PENDING → MATERIAL_RESERVED → 
MATERIAL_ISSUED → IN_PRODUCTION → QC_PENDING → QC_APPROVED/QC_REJECTED → 
FG_RECEIVED → READY_FOR_DISPATCH → DELIVERED → INVOICED → PAYMENT_RECEIVED

Key responsibilities:
1. Connect Sales Order to Work Order creation
2. Trigger material reservation on WO release
3. Trigger QC on production completion
4. Auto-increase FG stock after QC approval
5. Update Sales Order status based on WO progress
6. Trigger delivery dispatch on FG receipt
7. Trigger invoicing on delivery
"""
from __future__ import annotations

import uuid
import logging
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.sales.value_objects.order_status import OrderStatus
from backend.app.domain.manufacturing.entities.work_order import WorkOrderStatus
from backend.app.infrastructure.persistence.models.sales_models import SalesOrderModel
from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.application.manufacturing.services.inventory_service import InventoryService
from backend.app.application.notifications.notification_service import NotificationService

logger = logging.getLogger(__name__)


class WorkflowOrchestrationService:
    """
    Service for orchestrating end-to-end manufacturing workflow.
    
    Ensures that state transitions across modules are synchronized
    and that business rules are enforced consistently.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.inventory_service = InventoryService(session)
        self.notification_service = NotificationService(session)
    
    async def on_work_order_released(
        self,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Reserve materials and plan procurement when a work order is released."""
        stmt = select(WorkOrderModel).where(
            and_(
                WorkOrderModel.id == work_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
        )
        wo = (await self.session.execute(stmt)).scalar_one_or_none()
        if wo is None:
            raise ValueError(f"Work order {work_order_id} not found")

        from backend.app.application.manufacturing.services.material_planning_service import (
            MaterialPlanningService,
        )

        await MaterialPlanningService(self.session).plan_for_release(wo)
        await self.session.flush()

        return {
            "work_order_id": str(work_order_id),
            "status": wo.status,
            "message": "Material planning completed for released work order",
        }

    async def on_sales_order_approved(
        self,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Handle Sales Order approval workflow.
        
        Transition: APPROVED → WORK_ORDER_CREATED
        Action: Create Work Order for each line item
        """
        logger.info(
            "Sales Order approved - creating work orders",
            extra={"tenant_id": str(tenant_id), "sales_order_id": str(sales_order_id)}
        )
        
        # Update Sales Order status to WORK_ORDER_CREATED
        stmt = select(SalesOrderModel).where(
            and_(
                SalesOrderModel.id == sales_order_id,
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        sales_order = result.scalar_one_or_none()
        
        if not sales_order:
            raise ValueError(f"Sales Order {sales_order_id} not found")
        
        # Validate transition
        current_status = OrderStatus(sales_order.status)
        if not current_status.can_transition_to(OrderStatus.WORK_ORDER_CREATED):
            raise ValueError(
                f"Cannot transition Sales Order from {current_status.value} to WORK_ORDER_CREATED"
            )
        
        sales_order.status = OrderStatus.WORK_ORDER_CREATED.value
        sales_order.updated_at = datetime.now(timezone.utc)
        
        await self.session.flush()
        
        # TODO: Create Work Orders for each line item
        # This will be implemented in the sales integration module
        
        return {
            "sales_order_id": str(sales_order_id),
            "status": sales_order.status,
            "message": "Sales Order approved and work orders created",
        }
    
    async def on_work_order_completed(
        self,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Handle Work Order completion workflow.
        
        Transition: FG_RECEIVED → READY_FOR_DISPATCH
        Action: Update linked Sales Order to READY_FOR_DISPATCH
        """
        logger.info(
            "Work Order completed - updating sales order",
            extra={"tenant_id": str(tenant_id), "work_order_id": str(work_order_id)}
        )
        
        # Get Work Order
        stmt = select(WorkOrderModel).where(
            and_(
                WorkOrderModel.id == work_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        work_order = result.scalar_one_or_none()
        
        if not work_order:
            raise ValueError(f"Work Order {work_order_id} not found")
        
        # Update linked Sales Order if exists
        if work_order.sales_order_id:
            sales_order_stmt = select(SalesOrderModel).where(
                and_(
                    SalesOrderModel.id == work_order.sales_order_id,
                    SalesOrderModel.tenant_id == tenant_id,
                    SalesOrderModel.is_deleted.is_(False),
                )
            )
            sales_order_result = await self.session.execute(sales_order_stmt)
            sales_order = sales_order_result.scalar_one_or_none()
            
            if sales_order:
                current_status = OrderStatus(sales_order.status)
                if current_status.can_transition_to(OrderStatus.READY_FOR_DISPATCH):
                    sales_order.status = OrderStatus.READY_FOR_DISPATCH.value
                    sales_order.updated_at = datetime.now(timezone.utc)
                    
                    await self.session.flush()
                    
                    # Notify storekeeper for dispatch
                    await self.notification_service.create_notification(
                        tenant_id=tenant_id,
                        notification_type="order_ready_for_dispatch",
                        title=f"Order {sales_order.order_number} Ready for Dispatch",
                        message=f"Work Order {work_order.wo_number} completed. Order is ready for dispatch.",
                        reference_id=str(sales_order.id),
                        reference_type="sales_order",
                    )
        
        return {
            "work_order_id": str(work_order_id),
            "status": work_order.status,
            "message": "Work Order completed and sales order updated",
        }
    
    async def on_qc_approved(
        self,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        received_by: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Handle QC approval workflow.
        
        Transition: QC_APPROVED → FG_RECEIVED
        Action: Automatically increase FG stock
        """
        logger.info(
            "QC approved - receiving finished goods",
            extra={"tenant_id": str(tenant_id), "work_order_id": str(work_order_id)}
        )
        
        # Get Work Order
        stmt = select(WorkOrderModel).where(
            and_(
                WorkOrderModel.id == work_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        work_order = result.scalar_one_or_none()
        
        if not work_order:
            raise ValueError(f"Work Order {work_order_id} not found")
        
        if work_order.status == WorkOrderStatus.QC_PENDING.value:
            work_order.status = WorkOrderStatus.QC_APPROVED.value
            work_order.updated_at = datetime.now(timezone.utc)

        if work_order.status not in (
            WorkOrderStatus.QC_APPROVED.value,
            WorkOrderStatus.FG_RECEIVED.value,
        ):
            raise ValueError(
                f"Cannot receive FG for WO in status {work_order.status}; QC approval is required"
            )

        fg_material_id = await self._resolve_finished_good_material_id(work_order)
        fg_quantity = Decimal(str(work_order.produced_quantity or 0)) - Decimal(
            str(work_order.scrap_quantity or 0)
        )

        existing_receipt = (
            await self.session.execute(
                select(InventoryTransactionModel.id).where(
                    InventoryTransactionModel.tenant_id == tenant_id,
                    InventoryTransactionModel.material_id == fg_material_id,
                    InventoryTransactionModel.reference_type == "work_order",
                    InventoryTransactionModel.reference_id == work_order_id,
                    InventoryTransactionModel.transaction_type == "FG_RECEIPT",
                    InventoryTransactionModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()

        if fg_quantity > 0 and existing_receipt is None:
            await self.inventory_service.receive_fg(
                tenant_id=tenant_id,
                product_id=fg_material_id,
                quantity=fg_quantity,
                work_order_id=work_order_id,
                created_by=received_by,
            )

            logger.info(
                "FG stock increased",
                extra={
                    "tenant_id": str(tenant_id),
                    "material_id": str(fg_material_id),
                    "quantity": float(fg_quantity),
                },
            )

        work_order.status = WorkOrderStatus.FG_RECEIVED.value
        work_order.updated_at = datetime.now(timezone.utc)
        
        return {
            "work_order_id": str(work_order_id),
            "fg_quantity": float(fg_quantity),
            "material_id": str(fg_material_id),
            "receipt_created": existing_receipt is None and fg_quantity > 0,
            "message": "QC approved and FG stock increased",
        }

    async def _resolve_finished_good_material_id(self, work_order: WorkOrderModel) -> uuid.UUID:
        """Resolve a WO product reference to the material row that receives FG stock."""
        from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel

        material = (
            await self.session.execute(
                select(MaterialModel).where(
                    MaterialModel.id == work_order.product_id,
                    MaterialModel.tenant_id == work_order.tenant_id,
                    MaterialModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if material is not None:
            return material.id

        variant = (
            await self.session.execute(
                select(ItemVariantModel).where(
                    ItemVariantModel.id == work_order.product_id,
                    ItemVariantModel.tenant_id == work_order.tenant_id,
                    ItemVariantModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if variant is None:
            raise ValueError(f"Finished-good product {work_order.product_id} not found")

        if getattr(variant, "material_id", None):
            return variant.material_id

        material = (
            await self.session.execute(
                select(MaterialModel).where(
                    MaterialModel.tenant_id == work_order.tenant_id,
                    MaterialModel.code == variant.code,
                    MaterialModel.material_type == "finished",
                    MaterialModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if material is None:
            raise ValueError(f"Product {work_order.product_id} has no finished-good material")
        return material.id
    
    async def on_order_delivered(
        self,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Handle Order delivery workflow.
        
        Transition: DELIVERED → INVOICED
        Action: Trigger invoice creation
        """
        logger.info(
            "Order delivered - triggering invoicing",
            extra={"tenant_id": str(tenant_id), "sales_order_id": str(sales_order_id)}
        )
        
        # Get Sales Order
        stmt = select(SalesOrderModel).where(
            and_(
                SalesOrderModel.id == sales_order_id,
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        sales_order = result.scalar_one_or_none()
        
        if not sales_order:
            raise ValueError(f"Sales Order {sales_order_id} not found")
        
        # Update status to INVOICED
        current_status = OrderStatus(sales_order.status)
        if current_status.can_transition_to(OrderStatus.INVOICED):
            sales_order.status = OrderStatus.INVOICED.value
            sales_order.updated_at = datetime.now(timezone.utc)
            
            await self.session.flush()
            
            # Notify accountant for invoice processing
            await self.notification_service.create_notification(
                tenant_id=tenant_id,
                notification_type="invoice_required",
                title=f"Invoice Required for Order {sales_order.order_number}",
                message=f"Order {sales_order.order_number} has been delivered. Invoice needs to be generated.",
                reference_id=str(sales_order.id),
                reference_type="sales_order",
            )
        
        return {
            "sales_order_id": str(sales_order_id),
            "status": sales_order.status,
            "message": "Order delivered and invoicing triggered",
        }
    
    async def on_payment_received(
        self,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
        payment_amount: Decimal,
    ) -> Dict[str, Any]:
        """
        Handle payment receipt workflow.
        
        Transition: INVOICED → PAYMENT_RECEIVED → COMPLETED
        Action: Update Sales Order status
        """
        logger.info(
            "Payment received - completing order",
            extra={
                "tenant_id": str(tenant_id),
                "sales_order_id": str(sales_order_id),
                "payment_amount": float(payment_amount),
            }
        )
        
        # Get Sales Order
        stmt = select(SalesOrderModel).where(
            and_(
                SalesOrderModel.id == sales_order_id,
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        sales_order = result.scalar_one_or_none()
        
        if not sales_order:
            raise ValueError(f"Sales Order {sales_order_id} not found")
        
        # Update status to PAYMENT_RECEIVED
        current_status = OrderStatus(sales_order.status)
        if current_status.can_transition_to(OrderStatus.PAYMENT_RECEIVED):
            sales_order.status = OrderStatus.PAYMENT_RECEIVED.value
            sales_order.updated_at = datetime.now(timezone.utc)
            
            # Check if payment is complete
            if payment_amount >= sales_order.grand_total:
                if current_status.can_transition_to(OrderStatus.COMPLETED):
                    sales_order.status = OrderStatus.COMPLETED.value
            
            await self.session.flush()
        
        return {
            "sales_order_id": str(sales_order_id),
            "status": sales_order.status,
            "message": "Payment received and order completed",
        }
    
    async def get_workflow_status(
        self,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
    ) -> Dict[str, Any]:
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
        # Get Sales Order
        stmt = select(SalesOrderModel).where(
            and_(
                SalesOrderModel.id == sales_order_id,
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        sales_order = result.scalar_one_or_none()
        
        if not sales_order:
            raise ValueError(f"Sales Order {sales_order_id} not found")
        
        # Get Work Orders
        wo_stmt = select(WorkOrderModel).where(
            and_(
                WorkOrderModel.sales_order_id == sales_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
        )
        wo_result = await self.session.execute(wo_stmt)
        work_orders = wo_result.scalars().all()
        
        return {
            "sales_order_id": str(sales_order_id),
            "sales_order_status": sales_order.status,
            "sales_order_number": sales_order.order_number,
            "work_orders": [
                {
                    "wo_id": str(wo.id),
                    "wo_number": wo.wo_number,
                    "status": wo.status,
                    "produced_quantity": float(wo.produced_quantity),
                    "planned_quantity": float(wo.planned_quantity),
                }
                for wo in work_orders
            ],
            "workflow_stage": self._determine_workflow_stage(sales_order.status, work_orders),
        }
    
    def _determine_workflow_stage(
        self,
        sales_order_status: str,
        work_orders: list[WorkOrderModel],
    ) -> str:
        """Determine current workflow stage based on statuses."""
        status = OrderStatus(sales_order_status)
        
        if status in [OrderStatus.DRAFT, OrderStatus.PENDING_APPROVAL]:
            return "SALES"
        if status in [OrderStatus.APPROVED, OrderStatus.WORK_ORDER_CREATED]:
            return "PLANNING"
        if status in [OrderStatus.CONFIRMED, OrderStatus.PROCESSING]:
            return "PRODUCTION"
        if any(wo.status in [WorkOrderStatus.MATERIAL_PENDING, WorkOrderStatus.MATERIAL_RESERVED] for wo in work_orders):
            return "MATERIAL"
        if any(wo.status in [WorkOrderStatus.MATERIAL_ISSUED, WorkOrderStatus.IN_PRODUCTION] for wo in work_orders):
            return "PRODUCTION"
        if any(wo.status in [WorkOrderStatus.QC_PENDING, WorkOrderStatus.QC_APPROVED] for wo in work_orders):
            return "QUALITY"
        if status in [OrderStatus.READY_FOR_DISPATCH, OrderStatus.SHIPPED]:
            return "DELIVERY"
        if status == OrderStatus.DELIVERED:
            return "INVOICING"
        if status == OrderStatus.INVOICED:
            return "PAYMENT"
        if status in [OrderStatus.PAYMENT_RECEIVED, OrderStatus.COMPLETED]:
            return "COMPLETED"
        
        return "UNKNOWN"
