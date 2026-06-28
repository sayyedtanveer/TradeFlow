from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.application.finance.finance_service import FinanceService
from backend.app.application.inventory.services.stock_service import InventoryService
from backend.app.application.sales.inventory_integration import SalesInventoryIntegrationService
from backend.app.infrastructure.persistence.models.delivery_model import (
    DeliveryLineModel,
    DeliveryOrderModel,
)
from backend.app.infrastructure.persistence.models.sales_models import (
    SalesOrderLineModel,
    SalesOrderModel,
)


class DeliveryService:
    """Outbound delivery orchestration over sales and inventory models."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_from_sales_order(
        self,
        *,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
        created_by: uuid.UUID,
        lines: Optional[Iterable[dict]] = None,
        carrier: Optional[str] = None,
        tracking_number: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> DeliveryOrderModel:
        order = await self._sales_order_or_error(tenant_id, sales_order_id)
        requested = {uuid.UUID(str(item["sales_order_line_id"])): Decimal(str(item["quantity"])) for item in lines or []}
        line_models = await self._resolve_delivery_lines(order, requested)
        if not line_models:
            raise ValueError("No allocated quantity is available for delivery")

        delivery = DeliveryOrderModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            delivery_number=await self._next_delivery_number(tenant_id),
            sales_order_id=order.id,
            status="DRAFT",
            carrier=carrier,
            tracking_number=tracking_number,
            notes=notes,
            created_by=created_by,
        )
        self.session.add(delivery)
        await self.session.flush()

        for sales_line, quantity in line_models:
            self.session.add(
                DeliveryLineModel(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    delivery_order_id=delivery.id,
                    sales_order_line_id=sales_line.id,
                    variant_id=sales_line.product_id,
                    quantity=float(quantity),
                )
            )
        await self.session.flush()
        return await self.get(tenant_id, delivery.id)

    async def record_sales_shipment_document(
        self,
        *,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
        created_by: uuid.UUID,
        line_shipments: dict,
    ) -> DeliveryOrderModel:
        order = await self._sales_order_or_error(tenant_id, sales_order_id)
        requested = {uuid.UUID(str(line_id)): Decimal(str(qty)) for line_id, qty in line_shipments.items()}
        line_models = await self._resolve_delivery_lines(order, requested, allow_already_shipped=True)
        delivery = DeliveryOrderModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            delivery_number=await self._next_delivery_number(tenant_id),
            sales_order_id=order.id,
            status="SHIPPED",
            shipped_at=datetime.now(timezone.utc),
            notes="Created from sales shipment",
            created_by=created_by,
        )
        self.session.add(delivery)
        await self.session.flush()
        for sales_line, quantity in line_models:
            self.session.add(
                DeliveryLineModel(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    delivery_order_id=delivery.id,
                    sales_order_line_id=sales_line.id,
                    variant_id=sales_line.product_id,
                    quantity=float(quantity),
                )
            )
        await self.session.flush()
        return delivery

    async def ship(
        self,
        *,
        tenant_id: uuid.UUID,
        delivery_id: uuid.UUID,
        shipped_by: uuid.UUID,
        carrier: Optional[str] = None,
        tracking_number: Optional[str] = None,
    ) -> DeliveryOrderModel:
        delivery = await self.get(tenant_id, delivery_id)
        if delivery.status not in {"DRAFT", "PACKING"}:
            raise ValueError(f"Cannot ship delivery in {delivery.status} status")

        order = await self._sales_order_or_error(tenant_id, delivery.sales_order_id)
        lines_by_id = {line.id: line for line in order.lines}
        inventory = SalesInventoryIntegrationService(InventoryService(self.session), created_by=shipped_by)

        for delivery_line in delivery.lines:
            sales_line = lines_by_id.get(delivery_line.sales_order_line_id)
            if sales_line is None:
                raise ValueError(f"Sales line {delivery_line.sales_order_line_id} not found")
            quantity = Decimal(str(delivery_line.quantity))
            allocated = Decimal(str(sales_line.allocated_quantity or 0))
            shipped = Decimal(str(sales_line.shipped_quantity or 0))
            if shipped + quantity > allocated:
                raise ValueError("Delivery quantity exceeds allocated stock")
            await inventory.fulfill_reservation(
                tenant_id=tenant_id,
                reference_type="sales_order_line",
                reference_id=sales_line.id,
                quantity=quantity,
            )
            sales_line.shipped_quantity = float(shipped + quantity)
            sales_line.status = "shipped" if Decimal(str(sales_line.shipped_quantity)) >= allocated else sales_line.status
            sales_line.updated_at = datetime.now(timezone.utc)

        if all(Decimal(str(line.shipped_quantity or 0)) >= Decimal(str(line.allocated_quantity or 0)) for line in order.lines):
            order.status = "SHIPPED"
        order.updated_at = datetime.now(timezone.utc)
        delivery.status = "SHIPPED"
        delivery.carrier = carrier or delivery.carrier
        delivery.tracking_number = tracking_number or delivery.tracking_number
        delivery.shipped_at = datetime.now(timezone.utc)
        delivery.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return delivery

    async def deliver(
        self,
        *,
        tenant_id: uuid.UUID,
        delivery_id: uuid.UUID,
        delivered_by: uuid.UUID,
    ) -> DeliveryOrderModel:
        delivery = await self.get(tenant_id, delivery_id)
        if delivery.status != "SHIPPED":
            raise ValueError(f"Cannot deliver delivery in {delivery.status} status")

        order = await self._sales_order_or_error(tenant_id, delivery.sales_order_id)
        delivery.status = "DELIVERED"
        delivery.delivered_at = datetime.now(timezone.utc)
        delivery.updated_at = datetime.now(timezone.utc)

        should_invoice = all(
            Decimal(str(line.shipped_quantity or 0)) >= Decimal(str(line.quantity or 0)) for line in order.lines
        )
        if should_invoice:
            order.status = "DELIVERED"
            order.updated_at = datetime.now(timezone.utc)
        await self.session.flush()

        if should_invoice:
            await FinanceService(self.session).create_invoice_from_sales_order(
                tenant_id=tenant_id,
                sales_order_id=order.id,
                created_by=delivered_by,
                notes="Auto-generated on delivery completion.",
            )
            return await self.get(tenant_id, delivery_id)

        return delivery

    async def mark_sales_order_delivered_documents(self, tenant_id: uuid.UUID, sales_order_id: uuid.UUID) -> None:
        rows = (
            await self.session.execute(
                select(DeliveryOrderModel).where(
                    DeliveryOrderModel.tenant_id == tenant_id,
                    DeliveryOrderModel.sales_order_id == sales_order_id,
                    DeliveryOrderModel.status == "SHIPPED",
                    DeliveryOrderModel.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        now = datetime.now(timezone.utc)
        for delivery in rows:
            delivery.status = "DELIVERED"
            delivery.delivered_at = now
            delivery.updated_at = now
        await self.session.flush()

    async def get(self, tenant_id: uuid.UUID, delivery_id: uuid.UUID) -> DeliveryOrderModel:
        delivery = (
            await self.session.execute(
                select(DeliveryOrderModel)
                .options(selectinload(DeliveryOrderModel.lines))
                .where(
                    DeliveryOrderModel.id == delivery_id,
                    DeliveryOrderModel.tenant_id == tenant_id,
                    DeliveryOrderModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if delivery is None:
            raise ValueError("Delivery not found")
        return delivery

    async def list(self, tenant_id: uuid.UUID, sales_order_id: Optional[uuid.UUID] = None) -> list[DeliveryOrderModel]:
        query = (
            select(DeliveryOrderModel)
            .options(selectinload(DeliveryOrderModel.lines))
            .where(
                DeliveryOrderModel.tenant_id == tenant_id,
                DeliveryOrderModel.is_deleted.is_(False),
            )
        )
        if sales_order_id:
            query = query.where(DeliveryOrderModel.sales_order_id == sales_order_id)
        return (await self.session.execute(query.order_by(DeliveryOrderModel.created_at.desc()))).scalars().unique().all()

    async def _sales_order_or_error(self, tenant_id: uuid.UUID, sales_order_id: uuid.UUID) -> SalesOrderModel:
        order = (
            await self.session.execute(
                select(SalesOrderModel)
                .options(selectinload(SalesOrderModel.lines))
                .where(
                    SalesOrderModel.id == sales_order_id,
                    SalesOrderModel.tenant_id == tenant_id,
                    SalesOrderModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if order is None:
            raise ValueError("Sales order not found")
        return order

    async def _resolve_delivery_lines(
        self,
        order: SalesOrderModel,
        requested: dict[uuid.UUID, Decimal],
        *,
        allow_already_shipped: bool = False,
    ) -> list[tuple[SalesOrderLineModel, Decimal]]:
        result: list[tuple[SalesOrderLineModel, Decimal]] = []
        for sales_line in order.lines:
            allocated = Decimal(str(sales_line.allocated_quantity or 0))
            shipped = Decimal(str(sales_line.shipped_quantity or 0))
            available = allocated if allow_already_shipped else allocated - shipped
            if requested:
                if sales_line.id not in requested:
                    continue
                quantity = requested[sales_line.id]
            else:
                quantity = available
            if quantity <= 0:
                continue
            if not allow_already_shipped and quantity > available:
                raise ValueError(f"Delivery quantity exceeds available allocation for line {sales_line.id}")
            result.append((sales_line, quantity))
        return result

    async def _next_delivery_number(self, tenant_id: uuid.UUID) -> str:
        count = await self.session.scalar(
            select(func.count(DeliveryOrderModel.id)).where(DeliveryOrderModel.tenant_id == tenant_id)
        )
        return f"DO-{(count or 0) + 1:06d}"
