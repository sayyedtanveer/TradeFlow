"""Pydantic schemas for Warehouse API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Request Schemas ────────────────────────────────────────────────────────────


class AddressSchema(BaseModel):
    """Address input schema."""

    street: str = Field(..., min_length=1, max_length=200)
    city: str = Field(..., min_length=1, max_length=100)
    region: str = Field(..., min_length=1, max_length=100)
    postal_code: str = Field(..., min_length=1, max_length=20)
    country: str = Field(..., min_length=1, max_length=100)


class CreateWarehouseRequest(BaseModel):
    """Request body for creating a warehouse."""

    name: str = Field(..., min_length=1, max_length=100)
    address: AddressSchema
    phone: str = Field(..., min_length=1, max_length=50)
    email: Optional[str] = Field(None, max_length=255)


class UpdateWarehouseRequest(BaseModel):
    """Request body for updating a warehouse."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    address_street: Optional[str] = Field(None, min_length=1, max_length=200)
    address_city: Optional[str] = Field(None, min_length=1, max_length=100)
    address_region: Optional[str] = Field(None, min_length=1, max_length=100)
    address_postal_code: Optional[str] = Field(None, min_length=1, max_length=20)
    address_country: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[str] = Field(None, max_length=255)


class AssignUserRequest(BaseModel):
    """Request body for assigning a user to a warehouse."""

    user_id: uuid.UUID


# ── Response Schemas ───────────────────────────────────────────────────────────


class AddressResponse(BaseModel):
    """Address response schema."""

    street: str
    city: str
    region: str
    postal_code: str
    country: str


class WarehouseResponse(BaseModel):
    """Response schema for a single warehouse."""

    id: str
    tenant_id: str
    name: str
    address: AddressResponse
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class WarehouseListResponse(BaseModel):
    """Paginated list of warehouses."""

    items: List[WarehouseResponse]
    total: int
    page: int
    page_size: int


class UserAssignmentResponse(BaseModel):
    """Response schema for a user assignment."""

    id: str
    warehouse_id: str
    user_id: str
    assigned_at: str
    assigned_by: str


class WarehouseInventoryResponse(BaseModel):
    """Response for warehouse inventory view."""

    warehouse_id: str
    warehouse_name: str
    items: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int


class WarehouseOrdersResponse(BaseModel):
    """Response for warehouse orders view."""

    warehouse_id: str
    warehouse_name: str
    items: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
