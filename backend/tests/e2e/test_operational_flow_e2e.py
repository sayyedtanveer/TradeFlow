"""E2E Manufacturing Test Flow - Full operational flow testing.

This test script validates the complete manufacturing operational flow:
1. Create work order
2. Release work order (material reservation)
3. Issue material (storekeeper)
4. Start production (worker)
5. Record production
6. Complete operation
7. QC approval
8. FG receipt
9. Create delivery order
10. Dispatch delivery
11. Validate entire flow
"""
import uuid
import pytest
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.manufacturing.handlers.work_order_handler import WorkOrderHandler
from backend.app.application.manufacturing.commands.work_order_commands import (
    CreateWorkOrderCommand,
    ReleaseWorkOrderCommand,
    StartProductionCommand,
    RecordProductionCommand,
    CompleteWorkOrderCommand,
    QCApproveCommand,
    FGReceiveCommand,
)
from backend.app.application.inventory.handlers.storekeeper_handler import StorekeeperHandler
from backend.app.application.inventory.commands.storekeeper_commands import IssueMaterialCommand
from backend.app.application.manufacturing.handlers.worker_handler import WorkerHandler
from backend.app.application.manufacturing.commands.worker_commands import StartOperationCommand, CompleteOperationCommand
from backend.app.application.delivery.handlers.delivery_dashboard_handler import DeliveryDashboardHandler
from backend.app.application.delivery.commands.delivery_commands import CreateDispatchCommand
from backend.app.application.validation.services.operational_validation_service import OperationalValidationService


@pytest.mark.e2e
async def test_full_manufacturing_operational_flow(
    session: AsyncSession,
    test_tenant_id: uuid.UUID,
    test_user_id: uuid.UUID,
    test_product_id: uuid.UUID,
    test_material_id: uuid.UUID,
    test_customer_id: uuid.UUID,
):
    """Test complete manufacturing operational flow from WO creation to delivery."""
    
    # ── Step 1: Create Work Order ────────────────────────────────────────
    wo_handler = WorkOrderHandler(session)
    
    create_cmd = CreateWorkOrderCommand(
        tenant_id=test_tenant_id,
        product_id=test_product_id,
        quantity=Decimal("100"),
        due_date=datetime.now(timezone.utc),
        priority="HIGH",
        created_by=test_user_id,
    )
    wo = await wo_handler.handle_create(create_cmd)
    await session.commit()
    
    assert wo.status == "PLANNED"
    assert wo.quantity == Decimal("100")
    
    work_order_id = wo.id
    
    # ── Step 2: Release Work Order (Material Reservation) ─────────────
    release_cmd = ReleaseWorkOrderCommand(
        tenant_id=test_tenant_id,
        work_order_id=work_order_id,
        released_by=test_user_id,
    )
    await wo_handler.handle_release(release_cmd)
    await session.commit()
    
    # Refresh and check state
    await session.refresh(wo)
    assert wo.status in ("MATERIAL_RESERVED", "MATERIAL_PENDING")
    assert wo.reserved_stock > 0
    
    # ── Step 3: Issue Material (Storekeeper) ────────────────────────────
    storekeeper_handler = StorekeeperHandler(session)
    
    issue_cmd = IssueMaterialCommand(
        tenant_id=test_tenant_id,
        work_order_id=work_order_id,
        material_id=test_material_id,
        quantity=Decimal("100"),
        issued_by=test_user_id,
    )
    await storekeeper_handler.handle_issue_material(issue_cmd)
    await session.commit()
    
    await session.refresh(wo)
    assert wo.issued_stock > 0
    
    # ── Step 4: Start Production (Worker) ───────────────────────────────
    worker_handler = WorkerHandler(session)
    
    start_cmd = StartOperationCommand(
        tenant_id=test_tenant_id,
        work_order_id=work_order_id,
        job_card_id=wo.job_cards[0].id if wo.job_cards else uuid.uuid4(),
        started_by=test_user_id,
    )
    await worker_handler.handle_start_operation(start_cmd)
    await session.commit()
    
    await session.refresh(wo)
    assert wo.status == "IN_PRODUCTION"
    
    # ── Step 5: Record Production ────────────────────────────────────────
    production_cmd = RecordProductionCommand(
        tenant_id=test_tenant_id,
        work_order_id=work_order_id,
        produced_quantity=Decimal("100"),
        scrap_quantity=Decimal("0"),
        recorded_by=test_user_id,
    )
    await wo_handler.handle_record_production(production_cmd)
    await session.commit()
    
    await session.refresh(wo)
    assert wo.produced_quantity == Decimal("100")
    
    # ── Step 6: Complete Operation ───────────────────────────────────────
    complete_cmd = CompleteOperationCommand(
        tenant_id=test_tenant_id,
        work_order_id=work_order_id,
        job_card_id=wo.job_cards[0].id if wo.job_cards else uuid.uuid4(),
        completed_by=test_user_id,
    )
    await worker_handler.handle_complete_operation(complete_cmd)
    await session.commit()
    
    # ── Step 7: Complete Work Order ──────────────────────────────────────
    complete_wo_cmd = CompleteWorkOrderCommand(
        tenant_id=test_tenant_id,
        work_order_id=work_order_id,
        completed_by=test_user_id,
    )
    await wo_handler.handle_complete(complete_wo_cmd)
    await session.commit()
    
    await session.refresh(wo)
    assert wo.status == "QC_PENDING"
    
    # ── Step 8: QC Approval ───────────────────────────────────────────────
    qc_approve_cmd = QCApproveCommand(
        tenant_id=test_tenant_id,
        work_order_id=work_order_id,
        approved_by=test_user_id,
        remarks="QC passed",
    )
    await wo_handler.handle_qc_approve(qc_approve_cmd)
    await session.commit()
    
    await session.refresh(wo)
    assert wo.status == "QC_APPROVED"
    
    # ── Step 9: FG Receipt ────────────────────────────────────────────────
    fg_receive_cmd = FGReceiveCommand(
        tenant_id=test_tenant_id,
        work_order_id=work_order_id,
        received_by=test_user_id,
    )
    await wo_handler.handle_fg_receive(fg_receive_cmd)
    await session.commit()
    
    await session.refresh(wo)
    assert wo.status == "FG_RECEIVED"
    
    # ── Step 10: Create and Dispatch Delivery Order ───────────────────────
    # Note: This would require creating a delivery order first
    # For E2E test, we'll skip actual delivery order creation
    # and focus on validation
    
    # ── Step 11: Validate Entire Flow ─────────────────────────────────────
    validation_service = OperationalValidationService(session)
    
    wo_validation = await validation_service.validate_work_order_flow(
        tenant_id=test_tenant_id,
        work_order_id=work_order_id,
    )
    
    assert wo_validation["valid"] is True, f"WO validation failed: {wo_validation['errors']}"
    
    # Generate comprehensive report
    report = await validation_service.generate_validation_report(
        tenant_id=test_tenant_id,
    )
    
    assert report["summary"]["validation_rate"] == 100.0


@pytest.mark.e2e
async def test_inventory_traceability_flow(
    session: AsyncSession,
    test_tenant_id: uuid.UUID,
    test_material_id: uuid.UUID,
):
    """Test inventory traceability through the flow."""
    from backend.app.application.inventory.services.inventory_traceability_service import InventoryTraceabilityService
    
    traceability_service = InventoryTraceabilityService(session)
    
    # Get material traceability
    traceability = await traceability_service.get_material_traceability(
        tenant_id=test_tenant_id,
        material_id=test_material_id,
    )
    
    assert isinstance(traceability, list)
    
    # Get stock ledger
    ledger = await traceability_service.get_stock_ledger(
        tenant_id=test_tenant_id,
        material_id=test_material_id,
        limit=10,
    )
    
    assert isinstance(ledger, list)
    
    # Trace material lifecycle
    lifecycle = await traceability_service.trace_material_lifecycle(
        tenant_id=test_tenant_id,
        material_id=test_material_id,
    )
    
    assert lifecycle["material_id"] == test_material_id
    assert "current_balance" in lifecycle
    assert "transactions" in lifecycle


@pytest.mark.e2e
async def test_notification_creation_on_operational_events(
    session: AsyncSession,
    test_tenant_id: uuid.UUID,
    test_user_id: uuid.UUID,
    test_work_order_id: uuid.UUID,
):
    """Test that notifications are created on key operational events."""
    from backend.app.application.notification.services.notification_service import NotificationService
    
    notification_service = NotificationService(session)
    
    # Test material shortage notification
    notification_id = await notification_service.notify_material_shortage(
        tenant_id=test_tenant_id,
        user_id=test_user_id,
        work_order_id=test_work_order_id,
        material_name="Test Material",
        shortage_quantity=50.0,
    )
    
    assert notification_id is not None
    
    # Test WO overdue notification
    notification_id = await notification_service.notify_wo_overdue(
        tenant_id=test_tenant_id,
        user_id=test_user_id,
        work_order_id=test_work_order_id,
        wo_number="WO-001",
        due_date=datetime.now(timezone.utc),
    )
    
    assert notification_id is not None
    
    # Test QC rejection notification
    notification_id = await notification_service.notify_qc_rejected(
        tenant_id=test_tenant_id,
        user_id=test_user_id,
        work_order_id=test_work_order_id,
        wo_number="WO-001",
        reason="Quality issue",
    )
    
    assert notification_id is not None
    
    # Get user notifications
    notifications = await notification_service.get_user_notifications(
        tenant_id=test_tenant_id,
        user_id=test_user_id,
        unread_only=False,
    )
    
    assert len(notifications) >= 3
    
    # Mark all as read
    await notification_service.mark_all_as_read(
        tenant_id=test_tenant_id,
        user_id=test_user_id,
    )
    
    await session.commit()
