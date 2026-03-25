import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class WorkstationCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    capacity_hours_per_day: float = Field(8.0, ge=0)
    hourly_rate: float = Field(0.0, ge=0)

class WorkstationResponse(WorkstationCreate):
    id: uuid.UUID
    tenant_id: uuid.UUID
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class OperationCreate(BaseModel):
    name: str = Field(..., max_length=255)
    workstation_id: uuid.UUID
    setup_time: float = Field(0.0, ge=0)
    run_time: float = Field(0.0, ge=0)
    description: Optional[str] = None

class OperationResponse(OperationCreate):
    id: uuid.UUID
    tenant_id: uuid.UUID
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class BOMOperationAttach(BaseModel):
    operation_id: uuid.UUID
    sequence: int = Field(..., ge=1)
