"""Sales API routes (FastAPI endpoints) with full Dependency Injection."""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.app.domain.sales.repositories.client_repository import ClientRepository
from backend.app.domain.sales.repositories.sales_order_repository import SalesOrderRepository
from backend.app.domain.sales.repositories.price_list_repository import PriceListRepository
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_tenant_id,
    get_current_user_id,
)

from backend.app.interfaces.api.sales.schemas import (
    ClientCreateRequest,
    ClientUpdateRequest,
    ClientResponse,
    ClientListResponse,
    ClientCreditCheckResponse,
    PriceListRequest,
    PriceListLineRequest,
    PriceListResponse,
    PriceListListResponse,
    SalesOrderCreateRequest,
    SalesOrderResponse,
    SalesOrderListResponse,
    SalesOrderLineCreateRequest,
    ApplyDiscountRequest,
    ConfirmOrderRequest,
    ShipOrderRequest,
    CancelOrderRequest,
    OrderStatusResponse,
)
from backend.app.application.sales import (
    # Commands
    CreateClientCommand,
    UpdateClientCommand,
    DeactivateClientCommand,
    CreatePriceListCommand,
    AddPriceListLineCommand,
    UpdatePriceListLineCommand,
    RemovePriceListLineCommand,
    CreateSalesOrderCommand,
    AddLineToSalesOrderCommand,
    RemoveLineFromSalesOrderCommand,
    ApplyDiscountToOrderCommand,
    ConfirmSalesOrderCommand,
    CancelSalesOrderCommand,
    ShipOrderCommand,
    DeliverOrderCommand,
    # Queries
    GetClientByIdQuery,
    GetClientByCodeQuery,
    ListClientsQuery,
    GetSalesOrderByIdQuery,
    GetSalesOrderByNumberQuery,
    ListClientOrdersQuery,
    ListOrdersByDateRangeQuery,
    ListDraftOrdersQuery,
    ListOrdersByDeliveryDateQuery,
    GetProductPriceQuery,
    CheckClientCreditQuery,
    GetPriceListByIdQuery,
    ListPriceListsQuery,
    GetOrderCountByStatusQuery,
    # Handlers
    CreateClientCommandHandler,
    UpdateClientCommandHandler,
    DeactivateClientCommandHandler,
    CreatePriceListCommandHandler,
    AddPriceListLineCommandHandler,
    UpdatePriceListLineCommandHandler,
    RemovePriceListLineCommandHandler,
    CreateSalesOrderCommandHandler,
    AddLineToSalesOrderCommandHandler,
    RemoveLineFromSalesOrderCommandHandler,
    ApplyDiscountToOrderCommandHandler,
    ConfirmSalesOrderCommandHandler,
    CancelSalesOrderCommandHandler,
    ShipOrderCommandHandler,
    DeliverOrderCommandHandler,
    GetClientByIdQueryHandler,
    GetClientByCodeQueryHandler,
    ListClientsQueryHandler,
    GetSalesOrderByIdQueryHandler,
    GetSalesOrderByNumberQueryHandler,
    ListClientOrdersQueryHandler,
    ListOrdersByDateRangeQueryHandler,
    ListDraftOrdersQueryHandler,
    ListOrdersByDeliveryDateQueryHandler,
    GetProductPriceQueryHandler,
    CheckClientCreditQueryHandler,
    GetPriceListByIdQueryHandler,
    ListPriceListsQueryHandler,
    GetOrderCountByStatusQueryHandler,
)

# Create router
router = APIRouter(prefix="/sales", tags=["sales"])
logger = logging.getLogger(__name__)


# ==================== CLIENT ENDPOINTS ====================

@router.post("/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    body: ClientCreateRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Create a new client."""
    container = get_container(request)
    async with container.session_factory() as session:
        client_repo = ClientRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = CreateClientCommandHandler(client_repo, uow)
        try:
            client_id = await handler.handle(
                CreateClientCommand(
                    tenant_id=tenant_id,
                    code=body.code,
                    name=body.name,
                    email=body.email,
                    phone=body.phone,
                    address=body.address,
                    gst_number=body.gst_number,
                    credit_limit=body.credit_limit,
                    payment_terms_days=body.payment_terms_days,
                )
            )
            client = await client_repo.get_by_id(UUID(str(client_id)), tenant_id)
            return client.to_dict() if client else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error creating client: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Creation failed")


@router.get("/clients/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Get client details."""
    container = get_container(request)
    async with container.session_factory() as session:
        client_repo = ClientRepository(session)
        handler = GetClientByIdQueryHandler(client_repo)
        try:
            return await handler.handle(
                GetClientByIdQuery(
                    tenant_id=tenant_id,
                    client_id=client_id,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            logger.exception(f"Error retrieving client {client_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Retrieval failed")


@router.get("/clients", response_model=ClientListResponse)
async def list_clients(
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List clients with pagination and filtering."""
    container = get_container(request)
    async with container.session_factory() as session:
        client_repo = ClientRepository(session)
        handler = ListClientsQueryHandler(client_repo)
        try:
            items = await handler.handle(
                ListClientsQuery(
                    tenant_id=tenant_id,
                    is_active=is_active,
                    search=search,
                    limit=limit,
                    offset=offset,
                )
            )
            total = len(items)  # Would typically come from repository count method
            return ClientListResponse(items=items, total=total, limit=limit, offset=offset)
        except Exception as e:
            logger.exception(f"Error listing clients: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="List retrieval failed")


@router.patch("/clients/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: UUID,
    body: ClientUpdateRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Update client information."""
    container = get_container(request)
    async with container.session_factory() as session:
        client_repo = ClientRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = UpdateClientCommandHandler(client_repo, uow)
        try:
            await handler.handle(
                UpdateClientCommand(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    name=body.name,
                    email=body.email,
                    phone=body.phone,
                    address=body.address,
                    gst_number=body.gst_number,
                    credit_limit=body.credit_limit,
                    payment_terms_days=body.payment_terms_days,
                )
            )
            client = await client_repo.get_by_id(client_id, tenant_id)
            return client.to_dict() if client else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error updating client {client_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Update failed")


@router.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_client(
    client_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Deactivate a client (soft delete)."""
    container = get_container(request)
    async with container.session_factory() as session:
        client_repo = ClientRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = DeactivateClientCommandHandler(client_repo, uow)
        try:
            await handler.handle(
                DeactivateClientCommand(
                    tenant_id=tenant_id,
                    client_id=client_id,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            logger.exception(f"Error deactivating client {client_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Deactivation failed")


@router.get("/clients/{client_id}/credit", response_model=ClientCreditCheckResponse)
async def check_client_credit(
    client_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    order_total: Optional[float] = None,
):
    """Check client credit availability."""
    container = get_container(request)
    async with container.session_factory() as session:
        client_repo = ClientRepository(session)
        handler = CheckClientCreditQueryHandler(client_repo)
        try:
            return await handler.handle(
                CheckClientCreditQuery(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    order_total=order_total,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error checking credit for client {client_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Credit check failed")


# ==================== SALES ORDER ENDPOINTS ====================

@router.post("/orders", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: SalesOrderCreateRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Create a new sales order."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = CreateSalesOrderCommandHandler(order_repo, uow)
        try:
            order_id = await handler.handle(
                CreateSalesOrderCommand(
                    tenant_id=tenant_id,
                    client_id=body.client_id,
                    order_date=body.order_date,
                    delivery_date=body.delivery_date,
                    created_by=str(user_id),
                    notes=body.notes,
                )
            )
            order = await order_repo.get_by_id(UUID(str(order_id)), tenant_id)
            return order.to_dict() if order else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error creating sales order: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Creation failed")


@router.get("/orders/draft", response_model=SalesOrderListResponse)
async def list_draft_orders(
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    limit: int = Query(50, ge=1, le=1000),
):
    """List draft orders waiting for confirmation."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        handler = ListDraftOrdersQueryHandler(order_repo)
        try:
            items = await handler.handle(
                ListDraftOrdersQuery(
                    tenant_id=tenant_id,
                    limit=limit,
                )
            )
            total = len(items)
            return SalesOrderListResponse(items=items, total=total, limit=limit, offset=0)
        except Exception as e:
            logger.exception(f"Error listing draft orders: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="List retrieval failed")


@router.get("/orders/{order_id}", response_model=SalesOrderResponse)
async def get_order(
    order_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Get order details with full information."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        handler = GetSalesOrderByIdQueryHandler(order_repo)
        try:
            return await handler.handle(
                GetSalesOrderByIdQuery(
                    tenant_id=tenant_id,
                    order_id=order_id,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            logger.exception(f"Error retrieving order {order_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Retrieval failed")


@router.get("/orders/number/{order_number}", response_model=SalesOrderResponse)
async def get_order_by_number(
    order_number: str,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Get order by order number."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        handler = GetSalesOrderByNumberQueryHandler(order_repo)
        try:
            return await handler.handle(
                GetSalesOrderByNumberQuery(
                    tenant_id=tenant_id,
                    order_number=order_number,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            logger.exception(f"Error retrieving order by number {order_number}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Retrieval failed")


@router.get("/orders", response_model=SalesOrderListResponse)
async def list_orders(
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    client_id: Optional[UUID] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List orders with filtering by client or date range."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        
        try:
            if client_id:
                handler = ListClientOrdersQueryHandler(order_repo)
                items = await handler.handle(
                    ListClientOrdersQuery(
                        tenant_id=tenant_id,
                        client_id=client_id,
                        status=status_filter,
                        limit=limit,
                        offset=offset,
                    )
                )
            elif start_date and end_date:
                handler = ListOrdersByDateRangeQueryHandler(order_repo)
                items = await handler.handle(
                    ListOrdersByDateRangeQuery(
                        tenant_id=tenant_id,
                        start_date=start_date,
                        end_date=end_date,
                        status=status_filter,
                        limit=limit,
                        offset=offset,
                    )
                )
            else:
                raise ValueError("Provide client_id or both start_date and end_date")
            
            total = len(items)  # Would typically come from repository count method
            return SalesOrderListResponse(items=items, total=total, limit=limit, offset=offset)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error listing orders: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="List retrieval failed")

@router.post("/orders/{order_id}/lines", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED)
async def add_order_line(
    order_id: UUID,
    body: SalesOrderLineCreateRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Add a line item to an order."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        
        price_list_repo = PriceListRepository(session)
        from backend.app.domain.sales.services.pricing_service import PricingService
        pricing_service = PricingService(price_list_repo)
        
        handler = AddLineToSalesOrderCommandHandler(order_repo, pricing_service, uow)
        try:
            await handler.handle(
                AddLineToSalesOrderCommand(
                    tenant_id=tenant_id,
                    sales_order_id=order_id,
                    product_id=body.product_id,
                    product_type=body.product_type,
                    uom_id=body.uom_id,
                    quantity=body.quantity,
                    tax_rate=body.tax_rate,
                )
            )
            order = await order_repo.get_by_id(order_id, tenant_id)
            return order.to_dict() if order else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error adding line to order {order_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Line addition failed")


@router.delete("/orders/{order_id}/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_order_line(
    order_id: UUID,
    line_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Remove a line from an order."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = RemoveLineFromSalesOrderCommandHandler(order_repo, uow)
        try:
            await handler.handle(
                RemoveLineFromSalesOrderCommand(
                    tenant_id=tenant_id,
                    sales_order_id=order_id,
                    line_id=line_id,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            logger.exception(f"Error removing line {line_id} from order {order_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Line removal failed")


@router.post("/orders/{order_id}/discount", response_model=SalesOrderResponse)
async def apply_discount(
    order_id: UUID,
    body: ApplyDiscountRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Apply discount to order."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = ApplyDiscountToOrderCommandHandler(order_repo, uow)
        try:
            await handler.handle(
                ApplyDiscountToOrderCommand(
                    tenant_id=tenant_id,
                    sales_order_id=order_id,
                    discount_amount=body.discount_amount,
                )
            )
            order = await order_repo.get_by_id(order_id, tenant_id)
            return order.to_dict() if order else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error applying discount to order {order_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Discount application failed")


@router.post("/orders/{order_id}/confirm", response_model=SalesOrderResponse)
async def confirm_order(
    order_id: UUID,
    body: ConfirmOrderRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Confirm order (DRAFT → CONFIRMED)."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        client_repo = ClientRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        
        from backend.app.domain.sales.services.credit_validation_service import CreditValidationService
        from backend.app.domain.sales.services.inventory_reservation_service import InventoryReservationService
        from backend.app.application.sales.manufacturing_integration import SalesManufacturingIntegrationService
        from backend.app.application.sales.inventory_integration import SalesInventoryIntegrationService
        from backend.app.application.manufacturing.handlers.work_order_handler import WorkOrderHandler
        from backend.app.application.manufacturing.services.inventory_service import InventoryService as StockInventoryService
        
        credit_service = CreditValidationService(client_repo)
        stock_inventory = StockInventoryService(session)
        wo_handler = WorkOrderHandler(session).with_uow(uow)
        inv_integ = SalesInventoryIntegrationService(stock_inventory, created_by=user_id)
        mfg_integ = SalesManufacturingIntegrationService(wo_handler, uow).with_event_dispatcher(container.event_dispatcher)
        inv_service = InventoryReservationService(inv_integ, mfg_integ)

        handler = ConfirmSalesOrderCommandHandler(order_repo, client_repo, credit_service, inv_service, uow)
        try:
            await handler.handle(
                ConfirmSalesOrderCommand(
                    tenant_id=tenant_id,
                    sales_order_id=order_id,
                    confirmed_by=body.confirmed_by,
                )
            )
            order = await order_repo.get_by_id(order_id, tenant_id)
            return order.to_dict() if order else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error confirming order {order_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Confirmation failed")


@router.post("/orders/{order_id}/ship", response_model=SalesOrderResponse)
async def ship_order(
    order_id: UUID,
    body: ShipOrderRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Record shipment for order."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        
        from backend.app.domain.sales.services.inventory_reservation_service import InventoryReservationService
        from backend.app.application.sales.manufacturing_integration import SalesManufacturingIntegrationService
        from backend.app.application.sales.inventory_integration import SalesInventoryIntegrationService
        from backend.app.application.manufacturing.handlers.work_order_handler import WorkOrderHandler
        from backend.app.application.manufacturing.services.inventory_service import InventoryService as StockInventoryService
        
        stock_inventory = StockInventoryService(session)
        wo_handler = WorkOrderHandler(session).with_uow(uow)
        inv_integ = SalesInventoryIntegrationService(stock_inventory, created_by=user_id)
        mfg_integ = SalesManufacturingIntegrationService(wo_handler, uow).with_event_dispatcher(container.event_dispatcher)
        inv_service = InventoryReservationService(inv_integ, mfg_integ)
        
        handler = ShipOrderCommandHandler(order_repo, inv_service, uow)
        try:
            await handler.handle(
                ShipOrderCommand(
                    tenant_id=tenant_id,
                    sales_order_id=order_id,
                    line_shipments=body.line_shipments,
                    shipped_by=body.shipped_by,
                )
            )
            order = await order_repo.get_by_id(order_id, tenant_id)
            return order.to_dict() if order else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error shipping order {order_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Shipment recording failed")


@router.post("/orders/{order_id}/deliver", response_model=SalesOrderResponse)
async def deliver_order(
    order_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Record delivery of order."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = DeliverOrderCommandHandler(order_repo, uow)
        try:
            await handler.handle(
                DeliverOrderCommand(
                    tenant_id=tenant_id,
                    sales_order_id=order_id,
                    delivered_by=str(user_id),
                )
            )
            order = await order_repo.get_by_id(order_id, tenant_id)
            return order.to_dict() if order else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            logger.exception(f"Error delivering order {order_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Delivery recording failed")


@router.post("/orders/{order_id}/cancel", response_model=SalesOrderResponse)
async def cancel_order(
    order_id: UUID,
    body: CancelOrderRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Cancel an order."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        client_repo = ClientRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        
        from backend.app.domain.sales.services.credit_validation_service import CreditValidationService
        from backend.app.domain.sales.services.inventory_reservation_service import InventoryReservationService
        from backend.app.application.sales.manufacturing_integration import SalesManufacturingIntegrationService
        from backend.app.application.sales.inventory_integration import SalesInventoryIntegrationService
        from backend.app.application.manufacturing.handlers.work_order_handler import WorkOrderHandler
        from backend.app.application.manufacturing.services.inventory_service import InventoryService as StockInventoryService
        
        credit_service = CreditValidationService(client_repo)
        stock_inventory = StockInventoryService(session)
        wo_handler = WorkOrderHandler(session).with_uow(uow)
        inv_integ = SalesInventoryIntegrationService(stock_inventory, created_by=user_id)
        mfg_integ = SalesManufacturingIntegrationService(wo_handler, uow).with_event_dispatcher(container.event_dispatcher)
        inv_service = InventoryReservationService(inv_integ, mfg_integ)

        handler = CancelSalesOrderCommandHandler(order_repo, credit_service, inv_service, uow)
        try:
            await handler.handle(
                CancelSalesOrderCommand(
                    tenant_id=tenant_id,
                    sales_order_id=order_id,
                    reason=body.reason,
                    cancelled_by=body.cancelled_by,
                )
            )
            order = await order_repo.get_by_id(order_id, tenant_id)
            return order.to_dict() if order else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error cancelling order {order_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Cancellation failed")


@router.get("/orders/stats/by-status", response_model=OrderStatusResponse)
async def get_order_count_by_status(
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Get order counts by status."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        handler = GetOrderCountByStatusQueryHandler(order_repo)
        try:
            counts = await handler.handle(
                GetOrderCountByStatusQuery(
                    tenant_id=tenant_id,
                )
            )
            return OrderStatusResponse(**counts)
        except Exception as e:
            logger.exception(f"Error getting order counts by status: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stats retrieval failed")


# ==================== PRICE LIST ENDPOINTS ====================

@router.post("/price-lists", response_model=PriceListResponse, status_code=status.HTTP_201_CREATED)
async def create_price_list(
    body: PriceListRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Create a new price list."""
    container = get_container(request)
    async with container.session_factory() as session:
        price_list_repo = PriceListRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = CreatePriceListCommandHandler(price_list_repo, uow)
        try:
            price_list_id = await handler.handle(
                CreatePriceListCommand(
                    tenant_id=tenant_id,
                    name=body.name,
                    is_default=body.is_default,
                    valid_from=body.valid_from,
                    valid_to=body.valid_to,
                )
            )
            price_list = await price_list_repo.get_by_id(UUID(str(price_list_id)), tenant_id)
            return price_list.to_dict() if price_list else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error creating price list: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Creation failed")


@router.get("/price-lists/{price_list_id}", response_model=PriceListResponse)
async def get_price_list(
    price_list_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Get price list details."""
    container = get_container(request)
    async with container.session_factory() as session:
        price_list_repo = PriceListRepository(session)
        handler = GetPriceListByIdQueryHandler(price_list_repo)
        try:
            return await handler.handle(
                GetPriceListByIdQuery(
                    tenant_id=tenant_id,
                    price_list_id=price_list_id,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            logger.exception(f"Error retrieving price list {price_list_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Retrieval failed")


@router.get("/price-lists", response_model=PriceListListResponse)
async def list_price_lists(
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    is_default: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List price lists."""
    container = get_container(request)
    async with container.session_factory() as session:
        price_list_repo = PriceListRepository(session)
        handler = ListPriceListsQueryHandler(price_list_repo)
        try:
            items = await handler.handle(
                ListPriceListsQuery(
                    tenant_id=tenant_id,
                    is_default=is_default,
                    is_active=True,
                    limit=limit,
                    offset=offset,
                )
            )
            total = len(items)
            return PriceListListResponse(items=items, total=total, limit=limit, offset=offset)
        except Exception as e:
            logger.exception(f"Error listing price lists: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="List retrieval failed")


@router.post("/price-lists/{price_list_id}/lines", status_code=status.HTTP_201_CREATED)
async def add_price_list_line(
    price_list_id: UUID,
    body: PriceListLineRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Add a pricing line to a price list."""
    container = get_container(request)
    async with container.session_factory() as session:
        price_list_repo = PriceListRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = AddPriceListLineCommandHandler(price_list_repo, uow)
        try:
            await handler.handle(
                AddPriceListLineCommand(
                    tenant_id=tenant_id,
                    price_list_id=price_list_id,
                    product_id=body.product_id,
                    product_type=body.product_type,
                    unit_price=body.unit_price,
                )
            )
            price_list = await price_list_repo.get_by_id(price_list_id, tenant_id)
            return price_list.to_dict() if price_list else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error adding price list line: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Line addition failed")


@router.patch("/price-lists/{price_list_id}/lines", response_model=PriceListResponse)
async def update_price_list_line(
    price_list_id: UUID,
    body: PriceListLineRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Update a pricing line."""
    container = get_container(request)
    async with container.session_factory() as session:
        price_list_repo = PriceListRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = UpdatePriceListLineCommandHandler(price_list_repo, uow)
        try:
            await handler.handle(
                UpdatePriceListLineCommand(
                    tenant_id=tenant_id,
                    price_list_id=price_list_id,
                    product_id=body.product_id,
                    product_type=body.product_type,
                    new_price=body.unit_price,
                )
            )
            price_list = await price_list_repo.get_by_id(price_list_id, tenant_id)
            return price_list.to_dict() if price_list else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error updating price list line: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Line update failed")


@router.delete("/price-lists/{price_list_id}/lines/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_price_list_line(
    price_list_id: UUID,
    product_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Remove a pricing line from a price list."""
    container = get_container(request)
    async with container.session_factory() as session:
        price_list_repo = PriceListRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = RemovePriceListLineCommandHandler(price_list_repo, uow)
        try:
            await handler.handle(
                RemovePriceListLineCommand(
                    tenant_id=tenant_id,
                    price_list_id=price_list_id,
                    product_id=product_id,
                    product_type="PRODUCT",
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            logger.exception(f"Error removing price list line: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Line removal failed")
