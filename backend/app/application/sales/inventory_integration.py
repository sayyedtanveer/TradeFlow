"""Integration bridge connecting Sales reservations to canonical Inventory stock."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select

from backend.app.application.manufacturing.services.inventory_service import (
    InventoryService as StockInventoryService,
)
from backend.app.infrastructure.persistence.models.inventory_transaction_model import (
    InventoryTransactionModel,
)
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel

logger = logging.getLogger(__name__)


class SalesInventoryIntegrationService:
    """
    Adapter used by the Sales domain reservation service.

    Sales works with product variants, while stock is held as materials. The adapter
    resolves a sellable product to its finished-goods material and delegates all
    mutations to the canonical inventory service.
    """

    def __init__(
        self,
        inventory_service: StockInventoryService,
        *,
        created_by: Optional[UUID] = None,
    ):
        self.inventory_service = inventory_service
        self.created_by = created_by or UUID(int=0)

    async def _resolve_material(
        self,
        tenant_id: UUID,
        product_id: UUID,
        product_type: str,
    ) -> MaterialModel:
        session = self.inventory_service._session

        direct = await session.execute(
            select(MaterialModel).where(
                MaterialModel.id == product_id,
                MaterialModel.tenant_id == tenant_id,
                MaterialModel.is_deleted.is_(False),
            )
        )
        material = direct.scalar_one_or_none()
        if material is not None:
            return material

        if product_type == "variant":
            variant_result = await session.execute(
                select(ItemVariantModel).where(
                    ItemVariantModel.id == product_id,
                    ItemVariantModel.tenant_id == tenant_id,
                    ItemVariantModel.is_deleted.is_(False),
                )
            )
            variant = variant_result.scalar_one_or_none()
            if variant is not None:
                if getattr(variant, "material_id", None):
                    mapped_material_result = await session.execute(
                        select(MaterialModel).where(
                            MaterialModel.id == variant.material_id,
                            MaterialModel.tenant_id == tenant_id,
                            MaterialModel.is_deleted.is_(False),
                        )
                    )
                    mapped_material = mapped_material_result.scalar_one_or_none()
                    if mapped_material is not None:
                        return mapped_material

                material_result = await session.execute(
                    select(MaterialModel).where(
                        MaterialModel.tenant_id == tenant_id,
                        MaterialModel.code == variant.code,
                        MaterialModel.material_type == "finished",
                        MaterialModel.is_deleted.is_(False),
                    )
                )
                material = material_result.scalar_one_or_none()
                if material is not None:
                    return material

        raise ValueError(
            f"No inventory material is linked to {product_type} product {product_id}"
        )

    async def get_available_stock(
        self,
        tenant_id: UUID,
        product_id: UUID,
        product_type: str,
    ) -> Decimal:
        """Get available, unreserved stock for a sales product."""
        material = await self._resolve_material(tenant_id, product_id, product_type)
        return await self.inventory_service.get_available_stock(
            tenant_id=tenant_id,
            material_id=material.id,
        )

    async def reserve_stock(
        self,
        tenant_id: UUID,
        product_id: UUID,
        product_type: str,
        quantity: Decimal,
        uom_id: UUID,
        reference_type: str,
        reference_id: UUID,
    ) -> None:
        """Reserve stock for a sales order line without reducing physical stock."""
        if reference_type != "sales_order_line":
            logger.warning("Unexpected sales reservation reference_type=%s", reference_type)
        material = await self._resolve_material(tenant_id, product_id, product_type)
        await self.inventory_service.reserve_sales_stock(
            tenant_id=tenant_id,
            material_id=material.id,
            quantity=quantity,
            sales_order_line_id=reference_id,
            unit_id=uom_id,
            created_by=self.created_by,
        )

    async def release_stock(
        self,
        tenant_id: UUID,
        reference_type: str,
        reference_id: UUID,
        quantity: Decimal,
    ) -> None:
        """Release reserved sales stock by locating the original reservation."""
        session = self.inventory_service._session
        reservation_result = await session.execute(
            select(InventoryTransactionModel).where(
                InventoryTransactionModel.tenant_id == tenant_id,
                InventoryTransactionModel.reference_type == reference_type,
                InventoryTransactionModel.reference_id == reference_id,
                InventoryTransactionModel.transaction_type == "reserve",
                InventoryTransactionModel.is_deleted.is_(False),
            )
        )
        reservation = reservation_result.scalars().first()
        if reservation is None:
            return

        await self.inventory_service.release_sales_reservation(
            tenant_id=tenant_id,
            material_id=reservation.material_id,
            quantity=quantity,
            sales_order_line_id=reference_id,
            unit_id=reservation.unit_id,
            created_by=self.created_by,
        )

    async def fulfill_reservation(
        self,
        tenant_id: UUID,
        reference_type: str,
        reference_id: UUID,
        quantity: Decimal,
    ) -> None:
        """Convert a reservation into an actual sales shipment."""
        session = self.inventory_service._session
        reservation_result = await session.execute(
            select(InventoryTransactionModel).where(
                InventoryTransactionModel.tenant_id == tenant_id,
                InventoryTransactionModel.reference_type == reference_type,
                InventoryTransactionModel.reference_id == reference_id,
                InventoryTransactionModel.transaction_type == "reserve",
                InventoryTransactionModel.is_deleted.is_(False),
            )
        )
        reservation = reservation_result.scalars().first()
        if reservation is None:
            raise ValueError(f"No reservation found for {reference_type} {reference_id}")

        await self.inventory_service.fulfill_sales_reservation(
            tenant_id=tenant_id,
            material_id=reservation.material_id,
            quantity=quantity,
            sales_order_line_id=reference_id,
            unit_id=reservation.unit_id,
            created_by=self.created_by,
        )
