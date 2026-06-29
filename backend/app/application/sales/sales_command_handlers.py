"""Sales order command handlers (application orchestration)."""

from uuid import uuid4, UUID
from datetime import date, datetime, timezone

from backend.app.domain.sales.entities import SalesOrder, SalesOrderLine, Client
from backend.app.domain.sales.value_objects import OrderNumber, OrderStatus, Money
from backend.app.domain.sales.services import (
    PricingService,
    CreditValidationService,
    InventoryReservationService,
)
from backend.app.domain.sales.repositories import (
    SalesOrderRepository,
    ClientRepository,
    PriceListRepository,
)
from backend.app.application.sales.commands import (
    CreateSalesOrderCommand,
    AddLineToSalesOrderCommand,
    RemoveLineFromSalesOrderCommand,
    ApplyDiscountToOrderCommand,
    SubmitSalesOrderForApprovalCommand,
    ApproveSalesOrderCommand,
    RejectSalesOrderCommand,
    ConfirmSalesOrderCommand,
    CancelSalesOrderCommand,
    TransitionOrderToReadyCommand,
    ShipOrderCommand,
    DeliverOrderCommand,
    RecordPaymentCommand,
    CreateClientCommand,
    UpdateClientCommand,
    DeactivateClientCommand,
    CreatePriceListCommand,
    AddPriceListLineCommand,
    UpdatePriceListLineCommand,
    RemovePriceListLineCommand,
)


class CreateSalesOrderCommandHandler:
    """Handler for creating new sales orders."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        uow,  # Unit of Work for managing transactions
    ):
        """Initialize handler."""
        self.sales_order_repo = sales_order_repo
        self.uow = uow

    async def handle(self, command: CreateSalesOrderCommand) -> UUID:
        """
        Create a new sales order.
        
        Args:
            command: Create command
            
        Returns:
            Order ID
        """
        # Generate order number
        sequence = await self.sales_order_repo.get_next_sequence(
            tenant_id=command.tenant_id,
            date=command.order_date,
        )
        order_number = OrderNumber.generate(sequence)
        
        # Create order aggregate
        order_id = uuid4()
        order = SalesOrder(
            id=order_id,
            tenant_id=command.tenant_id,
            order_number=order_number,
            client_id=command.client_id,
            order_date=command.order_date,
            delivery_date=command.delivery_date,
            approver_id=command.approver_id,
        )
        order.created_by = command.created_by
        order.notes = command.notes
        
        # Persist order
        await self.sales_order_repo.save(order)
        
        # Dispatch domain events (handled in Unit of Work post-commit)
        await self.uow.work()
        
        return order_id


class AddLineToSalesOrderCommandHandler:
    """Handler for adding lines to sales orders."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        pricing_service: PricingService,
        uow,
    ):
        """Initialize handler."""
        self.sales_order_repo = sales_order_repo
        self.pricing_service = pricing_service
        self.uow = uow

    async def handle(self, command: AddLineToSalesOrderCommand) -> UUID:
        """
        Add a line to a sales order.
        
        Args:
            command: Add line command
            
        Returns:
            Line ID
            
        Raises:
            ValueError: If order not found or not in DRAFT status
        """
        # Fetch order
        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")
        
        # Get unit price from pricing service
        unit_price = await self.pricing_service.get_price(
            tenant_id=command.tenant_id,
            product_id=command.product_id,
            product_type=command.product_type,
            client_id=order.client_id,
            price_date=order.order_date,
        )
        
        # Create line entity
        line_id = uuid4()
        line = SalesOrderLine(
            id=line_id,
            order_id=order.id,
            product_id=command.product_id,
            product_type=command.product_type,
            uom_id=command.uom_id,
            quantity=command.quantity,
            unit_price=unit_price,
            tax_rate=command.tax_rate,
        )
        
        # Add line to order aggregate
        order.add_line(line)
        
        # Persist changes
        await self.sales_order_repo.save(order)
        await self.uow.work()
        
        return line_id


class RemoveLineFromSalesOrderCommandHandler:
    """Handler for removing lines from sales orders."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        uow,
    ):
        """Initialize handler."""
        self.sales_order_repo = sales_order_repo
        self.uow = uow

    async def handle(self, command: RemoveLineFromSalesOrderCommand) -> None:
        """
        Remove a line from a sales order.
        
        Args:
            command: Remove line command
        """
        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")
        
        order.remove_line(command.line_id)
        
        await self.sales_order_repo.save(order)
        await self.uow.work()


class ApplyDiscountToOrderCommandHandler:
    """Handler for applying discounts to orders."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        uow,
    ):
        """Initialize handler."""
        self.sales_order_repo = sales_order_repo
        self.uow = uow

    async def handle(self, command: ApplyDiscountToOrderCommand) -> None:
        """Apply discount to order."""
        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")
        
        order.apply_discount(command.discount_amount)
        
        await self.sales_order_repo.save(order)
        await self.uow.work()


class SubmitSalesOrderForApprovalCommandHandler:
    """Legacy handler — approval workflow is removed in the distribution model.
    
    In the new workflow, orders go directly from PENDING_INVENTORY_VALIDATION
    through automated validation. This handler is preserved for API backward
    compatibility but raises an error indicating the workflow has changed.
    """

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        uow,
    ):
        self.sales_order_repo = sales_order_repo
        self.uow = uow

    async def handle(self, command: SubmitSalesOrderForApprovalCommand) -> None:
        raise ValueError(
            "Approval workflow is no longer available. Orders are automatically "
            "validated through the inventory validation process."
        )


class ApproveSalesOrderCommandHandler:
    """Legacy handler — approval workflow is removed in the distribution model."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        uow,
    ):
        self.sales_order_repo = sales_order_repo
        self.uow = uow

    async def handle(self, command: ApproveSalesOrderCommand) -> None:
        raise ValueError(
            "Approval workflow is no longer available in the distribution model."
        )


class RejectSalesOrderCommandHandler:
    """Legacy handler — approval workflow is removed in the distribution model."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        uow,
    ):
        self.sales_order_repo = sales_order_repo
        self.uow = uow

    async def handle(self, command: RejectSalesOrderCommand) -> None:
        raise ValueError(
            "Approval workflow is no longer available in the distribution model."
        )


class ConfirmSalesOrderCommandHandler:
    """Handler for confirming sales orders (inventory validation and reservation)."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        client_repo: ClientRepository,
        credit_service: CreditValidationService,
        inventory_service: InventoryReservationService,
        uow,
        audit_service=None,
    ):
        """Initialize handler."""
        self.sales_order_repo = sales_order_repo
        self.client_repo = client_repo
        self.credit_service = credit_service
        self.inventory_service = inventory_service
        self.uow = uow
        self.audit_service = audit_service

    async def handle(self, command: ConfirmSalesOrderCommand) -> None:
        """
        Confirm a sales order: validate inventory, reserve stock, transition status.
        
        Business logic (Requirements 5.7, 6.3, 6.13):
        1. Validate order state (must be PENDING_INVENTORY_VALIDATION)
        2. Check client credit availability
        3. Allocate credit
        4. Reserve inventory for all lines — prevent overselling
        5. If any line has insufficient stock, cancel the order and release reservations
        6. If all stock available, transition to ASSIGNED
        
        Raises:
            ValueError: If validation fails or insufficient inventory
        """
        # Fetch order
        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")
        
        # 1. Validate state
        if order.status != OrderStatus.PENDING_INVENTORY_VALIDATION:
            raise ValueError(f"Cannot confirm order in {order.status.value} state")
        
        # 2. Check credit
        is_valid, reason = await self.credit_service.validate_credit(
            tenant_id=command.tenant_id,
            client_id=order.client_id,
            order_grand_total=order.grand_total,
        )
        if not is_valid:
            raise ValueError(f"Credit validation failed: {reason}")
        
        # 3. Allocate credit
        await self.credit_service.allocate_credit(
            tenant_id=command.tenant_id,
            client_id=order.client_id,
            amount=order.grand_total,
        )
        
        # 4. Reserve inventory for all lines — track shortages for overselling prevention
        shortage_items: list[dict] = []
        reserved_lines: list = []
        
        for line in order.lines:
            allocated_qty, shortage_qty, work_order_id = (
                await self.inventory_service.reserve_for_order_line(
                    tenant_id=command.tenant_id,
                    product_id=line.product_id,
                    product_type=line.product_type,
                    uom_id=line.uom_id,
                    quantity=line.quantity,
                    sales_order_id=order.id,
                    sales_order_line_id=line.id,
                    delivery_date=order.delivery_date,
                )
            )
            
            # Update line with allocations
            line.allocate(allocated_qty)
            if allocated_qty > 0:
                reserved_lines.append(line)
            
            if shortage_qty > 0:
                line.backorder(shortage_qty)
                shortage_items.append({
                    "product_id": str(line.product_id),
                    "requested": str(line.quantity),
                    "available": str(allocated_qty),
                    "shortage": str(shortage_qty),
                })
            
            if work_order_id:
                line.work_order_id = work_order_id
        
        # 5. If any item has a shortage, release all reservations and fail
        # (Requirement 6.3: reject and indicate which items have insufficient stock)
        if shortage_items:
            # Release reservations made so far
            await self.inventory_service.release_for_order(
                tenant_id=command.tenant_id,
                sales_order_id=order.id,
                lines=reserved_lines,
            )
            # Release allocated credit
            await self.credit_service.release_credit(
                tenant_id=command.tenant_id,
                client_id=order.client_id,
                amount=order.grand_total,
            )
            shortage_detail = "; ".join(
                f"product {s['product_id']}: requested {s['requested']}, available {s['available']}"
                for s in shortage_items
            )
            raise ValueError(
                f"Insufficient inventory for order {order.id}. "
                f"Shortages: {shortage_detail}"
            )
        
        # 6. All stock reserved successfully — transition to ASSIGNED
        previous_status = order.status
        order.transition_to(OrderStatus.ASSIGNED)
        
        # Persist all changes
        await self.sales_order_repo.save(order)
        await self.uow.work()

        # Record audit trail for the status transition
        if self.audit_service:
            from backend.app.domain.sales.services.order_state_machine import OrderStateMachine
            state_machine = OrderStateMachine(audit_service=self.audit_service)
            await state_machine._record_transition_audit(
                entity_id=order.id,
                previous_status=previous_status,
                new_status=OrderStatus.ASSIGNED,
                acting_user_id=None,  # System-driven transition
            )


class CancelSalesOrderCommandHandler:
    """Handler for cancelling sales orders."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        credit_service: CreditValidationService,
        inventory_service: InventoryReservationService,
        uow,
        audit_service=None,
    ):
        """Initialize handler."""
        self.sales_order_repo = sales_order_repo
        self.credit_service = credit_service
        self.inventory_service = inventory_service
        self.uow = uow
        self.audit_service = audit_service

    async def handle(self, command: CancelSalesOrderCommand) -> None:
        """
        Cancel a sales order.
        
        Business logic:
        1. Validate transition via state machine (raises InvalidTransitionError on failure)
        2. Release reserved inventory
        3. Release allocated credit
        4. Transition to CANCELLED
        5. Record transition in audit log
        """
        from backend.app.domain.sales.services.order_state_machine import (
            OrderStateMachine,
            InvalidTransitionError,
        )

        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")
        
        # Validate using the state machine — raises InvalidTransitionError (→ 409)
        state_machine = OrderStateMachine(audit_service=self.audit_service)
        state_machine.validate_transition(order.status, OrderStatus.CANCELLED)
        
        previous_status = order.status

        # Release inventory
        await self.inventory_service.release_for_order(
            tenant_id=command.tenant_id,
            sales_order_id=order.id,
            lines=order.lines,
        )
        
        # Release credit (only if order was in a state where credit was allocated)
        if order.status in (
            OrderStatus.ASSIGNED,
            OrderStatus.ACCEPTED,
            OrderStatus.PICKING,
            OrderStatus.PACKING,
            OrderStatus.READY_FOR_DISPATCH,
        ):
            await self.credit_service.release_credit(
                tenant_id=command.tenant_id,
                client_id=order.client_id,
                amount=order.grand_total,
            )
        
        # Cancel order
        order.cancel()
        
        await self.sales_order_repo.save(order)
        await self.uow.work()

        # Record audit trail for the transition
        await state_machine._record_transition_audit(
            entity_id=order.id,
            previous_status=previous_status,
            new_status=OrderStatus.CANCELLED,
            acting_user_id=getattr(command, 'cancelled_by', None),
        )


class ShipOrderCommandHandler:
    """Handler for shipping orders."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        inventory_service: InventoryReservationService,
        uow,
    ):
        """Initialize handler."""
        self.sales_order_repo = sales_order_repo
        self.inventory_service = inventory_service
        self.uow = uow

    async def handle(self, command: ShipOrderCommand) -> None:
        """
        Record shipment for an order.
        
        Args:
            command: Ship command with line-by-line shipment quantities
        """
        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")
        
        # Record shipments for each line
        for line in order.lines:
            shipment_key = line.id if line.id in command.line_shipments else str(line.id)
            if shipment_key in command.line_shipments:
                shipped_qty = command.line_shipments[shipment_key]
                
                # Record shipment
                line.ship(shipped_qty)
                
                # Update inventory
                await self.inventory_service.record_shipment(
                    tenant_id=command.tenant_id,
                    sales_order_line_id=line.id,
                    shipped_qty=shipped_qty,
                )
        
        # If all lines shipped, transition order to DISPATCHED via the new workflow.
        # In the distribution workflow, dispatch is handled by warehouse fulfilment (task 6.2).
        # This handler is kept for backward compatibility.
        all_shipped = bool(order.lines) and all(
            line.allocated_quantity > 0 and line.shipped_quantity >= line.allocated_quantity
            for line in order.lines
        )
        if all_shipped:
            if order.can_transition_to(OrderStatus.DISPATCHED):
                order.dispatch()
        
        await self.sales_order_repo.save(order)
        await self.uow.work()


class DeliverOrderCommandHandler:
    """Handler for delivering orders."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        uow,
    ):
        """Initialize handler."""
        self.sales_order_repo = sales_order_repo
        self.uow = uow

    async def handle(self, command: DeliverOrderCommand) -> None:
        """Record delivery of order (legacy — in new workflow dispatch covers this)."""
        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")
        
        # In the new distribution workflow, dispatch is the final physical step.
        # This handler is preserved for backward compatibility.
        if order.can_transition_to(OrderStatus.DISPATCHED):
            order.dispatch()
        
        await self.sales_order_repo.save(order)
        await self.uow.work()


# ── Admin Order Workflow Handlers ────────────────────────────────────────────


class AssignWarehouseCommandHandler:
    """Handler for admin manually assigning a warehouse to an order.

    Business logic (Requirements 6.13, 2.1):
    - Order must be in PENDING_MANUAL_ASSIGNMENT status
    - Validates warehouse exists and is active
    - Transitions order to ASSIGNED via state machine
    - Records transition in audit trail
    """

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        uow,
        audit_service=None,
    ):
        self.sales_order_repo = sales_order_repo
        self.uow = uow
        self.audit_service = audit_service

    async def handle(self, command) -> None:
        from backend.app.domain.sales.services.order_state_machine import OrderStateMachine

        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")

        # Use state machine to validate and execute transition with audit
        state_machine = OrderStateMachine(audit_service=self.audit_service)
        await state_machine.execute_transition(
            order=order,
            target_status=OrderStatus.ASSIGNED,
            acting_user_id=command.assigned_by,
        )

        # Set warehouse assignment fields
        from datetime import datetime, timezone
        order.assigned_warehouse_id = command.warehouse_id
        order.assigned_at = datetime.now(timezone.utc)

        await self.sales_order_repo.save(order)
        await self.uow.work()


class PlaceOrderOnHoldCommandHandler:
    """Handler for placing an order on hold.

    Business logic (Requirements 6.15, 2.1):
    - Order must be in ASSIGNED or ACCEPTED status
    - Transitions to ON_HOLD via state machine
    - Records hold_reason on the order
    - Records transition in audit trail
    """

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        uow,
        audit_service=None,
    ):
        self.sales_order_repo = sales_order_repo
        self.uow = uow
        self.audit_service = audit_service

    async def handle(self, command) -> None:
        from backend.app.domain.sales.services.order_state_machine import OrderStateMachine

        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")

        # Use state machine to validate and execute transition with audit
        state_machine = OrderStateMachine(audit_service=self.audit_service)
        await state_machine.execute_transition(
            order=order,
            target_status=OrderStatus.ON_HOLD,
            acting_user_id=command.held_by,
        )

        # Record hold reason
        order.hold_reason = command.hold_reason

        await self.sales_order_repo.save(order)
        await self.uow.work()


class ReleaseOrderHoldCommandHandler:
    """Handler for releasing an order from hold.

    Business logic (Requirements 6.16, 2.1):
    - Order must be in ON_HOLD status
    - Transitions back to ASSIGNED via state machine
    - Clears hold_reason
    - Records transition in audit trail
    """

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        uow,
        audit_service=None,
    ):
        self.sales_order_repo = sales_order_repo
        self.uow = uow
        self.audit_service = audit_service

    async def handle(self, command) -> None:
        from backend.app.domain.sales.services.order_state_machine import OrderStateMachine

        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")

        # Use state machine to validate and execute transition with audit
        state_machine = OrderStateMachine(audit_service=self.audit_service)
        await state_machine.execute_transition(
            order=order,
            target_status=OrderStatus.ASSIGNED,
            acting_user_id=command.released_by,
        )

        # Clear hold reason
        order.hold_reason = None

        await self.sales_order_repo.save(order)
        await self.uow.work()


class AdminCancelOrderCommandHandler:
    """Handler for admin cancelling an order.

    Business logic (Requirements 6.13, 2.1):
    - Order must be in PENDING_MANUAL_ASSIGNMENT or ASSIGNED status
    - Transitions to CANCELLED via state machine
    - Releases all inventory reservations
    - Records transition in audit trail
    - Caller is responsible for sending notification to Client
    """

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        inventory_service,
        uow,
        audit_service=None,
    ):
        self.sales_order_repo = sales_order_repo
        self.inventory_service = inventory_service
        self.uow = uow
        self.audit_service = audit_service

    async def handle(self, command) -> None:
        from backend.app.domain.sales.services.order_state_machine import OrderStateMachine

        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")

        # Use state machine to validate and execute transition with audit
        state_machine = OrderStateMachine(audit_service=self.audit_service)
        await state_machine.execute_transition(
            order=order,
            target_status=OrderStatus.CANCELLED,
            acting_user_id=command.cancelled_by,
        )

        # Release all inventory reservations for this order
        await self.inventory_service.release_all_reservations_for_order(
            tenant_id=command.tenant_id,
            order_id=command.sales_order_id,
            created_by=command.cancelled_by or UUID(int=0),
        )

        await self.sales_order_repo.save(order)
        await self.uow.work()

