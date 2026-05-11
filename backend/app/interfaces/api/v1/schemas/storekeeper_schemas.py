"""Storekeeper API schemas."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


# ── Queue Schemas ────────────────────────────────────────────────────────────

class IssueQueueResponse(BaseModel):
    """Pending material issue."""
    work_order_id: uuid.UUID
    wo_number: str
    material_id: uuid.UUID
    required_quantity: Decimal
    available_quantity: Decimal
    status: str


class ShortageQueueResponse(BaseModel):
    """Material shortage."""
    shortage_id: uuid.UUID
    work_order_id: uuid.UUID
    material_id: uuid.UUID
    required_quantity: Decimal
    available_quantity: Decimal
    shortage_quantity: Decimal
    status: str
    created_at: datetime


class PartiallyIssuedWOResponse(BaseModel):
    """Partially issued Work Order."""
    work_order_id: uuid.UUID
    wo_number: str
    product_id: uuid.UUID
    due_date: datetime
    status: str


# ── Request Schemas ───────────────────────────────────────────────────────────

class ReserveStockRequest(BaseModel):
    """Request to reserve stock."""
    work_order_id: uuid.UUID
    material_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    unit_id: Optional[uuid.UUID] = None


class IssueMaterialRequest(BaseModel):
    """Request to issue material."""
    work_order_id: uuid.UUID
    material_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    unit_id: Optional[uuid.UUID] = None


class PartialIssueRequest(BaseModel):
    """Request to partially issue material."""
    work_order_id: uuid.UUID
    material_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    unit_id: Optional[uuid.UUID] = None


class RejectIssueRequest(BaseModel):
    """Request to reject material issue."""
    work_order_id: uuid.UUID
    material_id: uuid.UUID
    reason: str


class ReturnMaterialRequest(BaseModel):
    """Request to return material."""
    work_order_id: uuid.UUID
    material_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    unit_id: Optional[uuid.UUID] = None
