"""Operational Validation Service - E2E operational flow validation."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
from backend.app.infrastructure.persistence.models.delivery_model import DeliveryOrderModel


class OperationalValidationService:
    """Service for E2E operational flow validation.

    Responsibilities:
    - Validate inventory flow
    - Validate delivery flow
    - Generate validation reports
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def validate_inventory_flow(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
    ) -> dict:
        """Validate inventory flow for a material."""
        stmt = select(InventoryTransactionModel).where(
            InventoryTransactionModel.tenant_id == tenant_id,
            InventoryTransactionModel.material_id == material_id,
            InventoryTransactionModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        transactions = result.scalars().all()

        errors = []
        warnings = []

        # Check for negative stock
        running_balance = 0
        for tx in transactions:
            if tx.transaction_type in ("receipt", "purchase_receipt", "transfer_in"):
                running_balance += tx.quantity
            elif tx.transaction_type in ("issue", "transfer_out", "dispatch"):
                running_balance -= tx.quantity

            if running_balance < 0:
                errors.append(f"Negative stock at transaction {tx.id}: {running_balance}")

        # Check for missing transactions
        if len(transactions) == 0:
            warnings.append("No inventory transactions found")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "material_id": str(material_id),
            "transaction_count": len(transactions),
            "current_balance": running_balance,
        }

    async def validate_delivery_flow(
        self,
        *,
        tenant_id: uuid.UUID,
        delivery_order_id: uuid.UUID,
    ) -> dict:
        """Validate delivery operational flow."""
        stmt = select(DeliveryOrderModel).where(
            DeliveryOrderModel.id == delivery_order_id,
            DeliveryOrderModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        do = result.scalar_one_or_none()

        if not do:
            return {"valid": False, "errors": ["Delivery order not found"]}

        errors = []
        warnings = []

        # Validate delivery flow
        if do.status == "DELIVERED":
            if not do.delivery_date:
                errors.append("Delivery marked as DELIVERED but no delivery date")
            if not do.shipped_at:
                errors.append("Delivery marked as DELIVERED but not shipped")
        elif do.status == "IN_TRANSIT":
            if not do.shipped_at:
                errors.append("Delivery marked as IN_TRANSIT but not shipped")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "delivery_order_id": str(delivery_order_id),
            "current_status": do.status,
        }
