"""API Schemas for Warehouse-Product Assignment."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional
import uuid


# ── Request Schemas ────────────────────────────────────────────────────────────

class AssignProductRequest(BaseModel):
    """Request to assign a product to a warehouse."""
    product_id: uuid.UUID = Field(..., description="Product ID (ItemTemplate ID)")
    default_reorder_level: int = Field(
        default=0,
        ge=0,
        description="Default reorder level for this warehouse-product combo",
    )


class UpdateReorderLevelRequest(BaseModel):
    """Request to update reorder level for warehouse-product combo."""
    default_reorder_level: int = Field(
        ...,
        ge=0,
        description="New default reorder level",
    )


# ── Response Schemas ──────────────────────────────────────────────────────────

class WarehouseProductAssignmentResponse(BaseModel):
    """Response for warehouse-product assignment."""
    id: str
    warehouse_id: str
    product_id: str
    is_available: bool = Field(description="Whether product is available in warehouse")
    default_reorder_level: int = Field(description="Default reorder level for this combo")

    class Config:
        from_attributes = True


class WarehouseProductAssignmentListResponse(BaseModel):
    """Response for listing warehouse-product assignments."""
    id: str
    warehouse_id: str
    product_id: str
    is_available: bool
    default_reorder_level: int
    product_name: Optional[str] = None
    product_code: Optional[str] = None

    class Config:
        from_attributes = True


class AvailableWarehouseResponse(BaseModel):
    """Response for available warehouses for a product."""
    warehouse_id: str
    warehouse_name: str
    is_available: bool
    default_reorder_level: int

    class Config:
        from_attributes = True


class ProductAvailabilityResponse(BaseModel):
    """Response showing all warehouses that have a product."""
    product_id: str
    product_name: str
    product_code: str
    available_warehouses: List[AvailableWarehouseResponse]
    total_warehouses: int = Field(description="Total number of warehouses with this product")

    class Config:
        from_attributes = True
