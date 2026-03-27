"""Commands for the Work Order application layer."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class CreateWorkOrderCommand(BaseModel):
    tenant_id: uuid.UUID
    product_id: uuid.UUID
    bom_id: uuid.UUID
    planned_quantity: Decimal = Field(..., gt=0)
    start_date: date
    due_date: date
    priority: str = "NORMAL"
    sales_order_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    created_by: uuid.UUID

    @model_validator(mode="after")
    def due_after_start(self) -> "CreateWorkOrderCommand":
        if self.due_date < self.start_date:
            raise ValueError("due_date must be on or after start_date")
        return self


class ReleaseWorkOrderCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID


class StartWorkOrderCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID


class IssueMaterialCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    material_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    unit_id: uuid.UUID
    issued_by: uuid.UUID


class RecordProductionCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    produced_quantity: Decimal = Field(..., gt=0)
    scrap_quantity: Decimal = Field(Decimal("0"), ge=0)
    notes: Optional[str] = None
    recorded_by: uuid.UUID


class CompleteWorkOrderCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID


class CloseWorkOrderCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID


class StartJobCardCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    job_card_id: uuid.UUID
    assigned_to: Optional[uuid.UUID] = None


class CompleteJobCardCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    job_card_id: uuid.UUID
    remarks: Optional[str] = None
