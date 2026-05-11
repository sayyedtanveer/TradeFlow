"""Worker API schemas."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


# ── Queue Schemas ────────────────────────────────────────────────────────────

class JobCardResponse(BaseModel):
    """Job card in worker queue."""
    job_card_id: uuid.UUID
    operation_id: uuid.UUID
    sequence: int
    status: str
    assigned_to: Optional[uuid.UUID] = None


class WorkerQueueResponse(BaseModel):
    """Work Order in worker queue."""
    work_order_id: uuid.UUID
    wo_number: str
    product_id: uuid.UUID
    due_date: datetime
    priority: str
    status: str
    job_cards: list[JobCardResponse]


# ── Request Schemas ───────────────────────────────────────────────────────────

class StartOperationRequest(BaseModel):
    """Request to start operation."""
    work_order_id: uuid.UUID
    job_card_id: uuid.UUID


class PauseOperationRequest(BaseModel):
    """Request to pause operation."""
    work_order_id: uuid.UUID
    job_card_id: uuid.UUID


class CompleteOperationRequest(BaseModel):
    """Request to complete operation."""
    work_order_id: uuid.UUID
    job_card_id: uuid.UUID
    remarks: Optional[str] = None


class ReportWastageRequest(BaseModel):
    """Request to report wastage."""
    work_order_id: uuid.UUID
    scrap_quantity: Decimal = Field(..., ge=0)
    notes: Optional[str] = None


class RecordProductionRequest(BaseModel):
    """Request to record production."""
    work_order_id: uuid.UUID
    produced_quantity: Decimal = Field(..., gt=0)
    scrap_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    notes: Optional[str] = None
