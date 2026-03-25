import uuid
from typing import Optional
from pydantic import BaseModel

class AddWorkstationCommand(BaseModel):
    tenant_id: uuid.UUID
    code: str
    name: str
    capacity_hours_per_day: float = 8.0
    hourly_rate: float = 0.0

class AddOperationCommand(BaseModel):
    tenant_id: uuid.UUID
    name: str
    workstation_id: uuid.UUID
    setup_time: float = 0.0
    run_time: float = 0.0
    description: Optional[str] = None

class AttachOperationToBOMCommand(BaseModel):
    tenant_id: uuid.UUID
    bom_id: uuid.UUID
    operation_id: uuid.UUID
    sequence: int
