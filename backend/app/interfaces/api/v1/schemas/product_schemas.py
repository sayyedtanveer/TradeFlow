from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


# ── Item Template ─────────────────────────────────────────────────────────────

class AttributeDefinition(BaseModel):
    key: str = Field(..., description="Attribute key, e.g. 'SIZE'")
    label: str = Field(..., description="Human-readable label, e.g. 'Size'")
    values: List[str] = Field(default_factory=list, description="Allowed values, e.g. ['S', 'M', 'L']")


class CreateItemTemplateRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    base_unit_id: Optional[uuid.UUID] = None
    attributes: List[AttributeDefinition] = Field(default_factory=list)


class UpdateItemTemplateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    base_unit_id: Optional[uuid.UUID] = None
    attributes: Optional[List[AttributeDefinition]] = None
    is_active: Optional[bool] = None


class ItemTemplateResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    description: Optional[str]
    category_id: Optional[uuid.UUID]
    base_unit_id: Optional[uuid.UUID]
    attributes: List[Dict[str, Any]]
    is_active: bool

    model_config = {"from_attributes": True}


class ItemTemplateListResponse(BaseModel):
    items: List[ItemTemplateResponse]
    total: int
    page: int
    page_size: int


# ── Item Variant ──────────────────────────────────────────────────────────────

class CreateItemVariantRequest(BaseModel):
    attribute_values: Dict[str, Any] = Field(
        ..., description="e.g. {\"SIZE\": \"SMALL\", \"COLOR\": \"RED\"}"
    )
    base_unit_id: Optional[uuid.UUID] = None
    standard_cost: Decimal = Decimal("0")
    selling_price: Optional[Decimal] = None


class UpdateItemVariantRequest(BaseModel):
    standard_cost: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    is_active: Optional[bool] = None


class ItemVariantResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    template_id: uuid.UUID
    code: str
    name: str
    variant_key: str
    attribute_values: Dict[str, Any]
    base_unit_id: Optional[uuid.UUID]
    standard_cost: Decimal
    selling_price: Optional[Decimal]
    is_active: bool

    model_config = {"from_attributes": True}


class ItemVariantListResponse(BaseModel):
    items: List[ItemVariantResponse]
    total: int
    page: int
    page_size: int


class ItemVariantSearchItem(ItemVariantResponse):
    """Variant row for global search — includes unit label and resolvable FG material id."""

    base_unit_code: Optional[str] = None
    stock_material_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Material id to use for receive/stock when linked (same id as variant or finished material with matching code).",
    )


class ItemVariantSearchListResponse(BaseModel):
    items: List[ItemVariantSearchItem]
    total: int
    page: int
    page_size: int
