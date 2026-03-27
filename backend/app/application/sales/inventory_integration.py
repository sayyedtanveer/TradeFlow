"""Integration bridge connecting Sales to Inventory for stock reservations."""
import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from backend.app.application.inventory.services.inventory_service import InventoryService as AppInventoryService
from backend.app.domain.inventory.value_objects import TransactionType

logger = logging.getLogger(__name__)


class SalesInventoryIntegrationService:
    """
    Implements the inventory_service interface required by InventoryReservationService.
    Bridges the Sales domain and Inventory application service.
    """

    def __init__(self, inventory_app_service: AppInventoryService):
        self.inventory_app_service = inventory_app_service

    async def get_available_stock(
        self,
        tenant_id: UUID,
        product_id: UUID,
        product_type: str,
    ) -> Decimal:
        """Get currently available unreserved stock."""
        # For our MVP, we query the current total quantity. 
        # (A full reserved/allocated table could be checked here)
        session = self.inventory_app_service._session
        from backend.app.infrastructure.persistence.models.inventory.stock_level_model import StockLevelModel
        from sqlalchemy import select, func
        
        stmt = select(func.sum(StockLevelModel.quantity)).where(
            StockLevelModel.tenant_id == tenant_id,
            StockLevelModel.material_id == product_id,
            StockLevelModel.is_deleted.is_(False)
        )
        result = await session.execute(stmt)
        qty = result.scalar_one_or_none()
        return Decimal(str(qty)) if qty else Decimal('0')

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
        """Reserve stock for a sales order line."""
        # Since we just use a simplified ledger, we will directly adjust to a "RESERVED" virtual location or 
        # just record a transaction. Let's use the adjustment to decrease stock.
        await self.inventory_app_service.record_transaction(
            tenant_id=tenant_id,
            material_id=product_id,
            unit_id=uom_id,
            transaction_type=TransactionType.ADJUSTMENT,
            quantity=-float(quantity),
            reference_id=reference_id,
            remarks=f"Reserved for {reference_type}",
            created_by=UUID(int=0)
        )

    async def release_stock(
        self,
        tenant_id: UUID,
        reference_type: str,
        reference_id: UUID,
        quantity: Decimal,
    ) -> None:
        """Release reserved stock back to available."""
        # Assuming we can find the uom and material_id from the reference
        # We will add the stock back via adjustment
        session = self.inventory_app_service._session
        from backend.app.infrastructure.persistence.models.inventory.transaction_model import InventoryTransactionModel
        from sqlalchemy import select
        
        stmt = select(InventoryTransactionModel).where(
            InventoryTransactionModel.tenant_id == tenant_id,
            InventoryTransactionModel.reference_id == reference_id
        ).limit(1)
        result = await session.execute(stmt)
        tx = result.scalar_one_or_none()
        
        if tx:
            await self.inventory_app_service.record_transaction(
                tenant_id=tenant_id,
                material_id=tx.material_id,
                unit_id=tx.unit_id,
                transaction_type=TransactionType.ADJUSTMENT,
                quantity=float(quantity),
                reference_id=reference_id,
                remarks=f"Released reservation from {reference_type}",
                created_by=UUID(int=0)
            )

    async def fulfill_reservation(
        self,
        tenant_id: UUID,
        reference_type: str,
        reference_id: UUID,
        quantity: Decimal,
    ) -> None:
        """Convert a reservation to actual shipped consumption."""
        # Since reserve_stock already decremented the physical level in our simple model, 
        # fulfilling it requires no physical ledger update, just an audit trace.
        session = self.inventory_app_service._session
        from backend.app.infrastructure.persistence.models.inventory.transaction_model import InventoryTransactionModel
        from sqlalchemy import select
        
        stmt = select(InventoryTransactionModel).where(
            InventoryTransactionModel.tenant_id == tenant_id,
            InventoryTransactionModel.reference_id == reference_id
        ).limit(1)
        result = await session.execute(stmt)
        tx = result.scalar_one_or_none()
        
        if tx:
            await self.inventory_app_service.record_transaction(
                tenant_id=tenant_id,
                material_id=tx.material_id,
                unit_id=tx.unit_id,
                transaction_type=TransactionType.ISSUE,
                quantity=0.0, # zero quantity because reserve already decremented it
                reference_id=reference_id,
                remarks=f"Fulfilled {quantity} for {reference_type}",
                created_by=UUID(int=0)
            )
