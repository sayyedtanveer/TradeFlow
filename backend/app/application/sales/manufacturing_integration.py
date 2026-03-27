"""Integration bridge connecting Sales to Manufacturing for automatic Work Order creation."""
import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from backend.app.application.manufacturing.commands.work_order_commands import CreateWorkOrderCommand
from backend.app.application.manufacturing.handlers.work_order_handler import WorkOrderHandler

logger = logging.getLogger(__name__)


class SalesManufacturingIntegrationService:
    """
    Implements the manufacturing_service interface required by InventoryReservationService.
    Bridges the Sales domain and Manufacturing domain.
    """

    def __init__(self, wo_handler: WorkOrderHandler):
        self.wo_handler = wo_handler

    async def create_work_order(
        self,
        tenant_id: UUID,
        product_id: UUID,
        product_type: str,
        quantity: Decimal,
        uom_id: UUID,
        due_date,
        sales_order_line_id: UUID,
    ) -> Optional[UUID]:
        """
        Creates a Work Order to fulfill a Sales shortage.
        Assumes product_id is an item_variant with a default BOM.
        """
        try:
            # We need the default BOM for this product_id.
            # WorkOrderHandler's handle_create accepts a CreateWorkOrderCommand 
            # which expects bom_id. We need to find the default BOM first.
            session = self.wo_handler._session
            # We must import BOM models here to avoid circular imports at top level
            from backend.app.infrastructure.persistence.models.bom_model import BOMModel
            from sqlalchemy import select

            stmt = select(BOMModel).where(
                BOMModel.tenant_id == tenant_id,
                BOMModel.item_variant_id == product_id,
                BOMModel.is_active.is_(True)
            ).order_by(BOMModel.created_at.desc()).limit(1)
            
            result = await session.execute(stmt)
            bom = result.scalar_one_or_none()

            if not bom:
                logger.warning(f"No active BOM found for product {product_id}. Cannot auto-create Work Order.")
                return None

            # Calculate start date as due_date - 7 days (simple heuristic for now)
            from datetime import timedelta
            start_date = due_date - timedelta(days=7)

            cmd = CreateWorkOrderCommand(
                tenant_id=tenant_id,
                product_id=product_id,
                bom_id=bom.id,
                planned_quantity=quantity,
                start_date=start_date,
                due_date=due_date,
                priority="HIGH",  # Shortages are high priority
                sales_order_id=sales_order_line_id, # Linking SO Line
                created_by=UUID(int=0), # System user
                notes=f"Auto-generated for Sales shortage."
            )
            wo_id = await self.wo_handler.handle_create(cmd)
            logger.info(f"Successfully auto-created Work Order {wo_id} for Sales shortage.")
            return wo_id

        except Exception as e:
            logger.error(f"Auto Work Order creation failed for product {product_id}: {str(e)}")
            return None
