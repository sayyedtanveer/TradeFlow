"""API Schemas for Stock Aggregation."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional
import uuid


# ── Response Schemas ──────────────────────────────────────────────────────────

class WarehouseStockResponse(BaseModel):
    """Stock info for product in a warehouse."""
    warehouse_id: str
    warehouse_name: Optional[str] = None
    is_available: bool
    default_reorder_level: int


class ProductAvailabilityResponse(BaseModel):
    """Product availability across all warehouses."""
    product_id: str
    product_name: Optional[str] = None
    product_code: Optional[str] = None
    is_available_anywhere: bool = Field(
        description="True if product is available in at least one warehouse"
    )
    available_warehouse_count: int
    total_warehouses: Optional[int] = None
    warehouses: List[WarehouseStockResponse] = Field(
        default_factory=list,
        description="List of warehouses that stock this product",
    )


class ProductInWarehouseResponse(BaseModel):
    """Product info as stocked in a warehouse."""
    product_id: str
    product_name: Optional[str] = None
    product_code: Optional[str] = None
    is_available: bool
    default_reorder_level: int


class WarehouseStockListResponse(BaseModel):
    """Warehouse inventory summary."""
    warehouse_id: str
    warehouse_name: Optional[str] = None
    product_count: int
    products: List[ProductInWarehouseResponse] = Field(
        default_factory=list,
        description="Products stocked at this warehouse",
    )


class CoverageAnalysisResponse(BaseModel):
    """Analysis of product-warehouse coverage."""
    total_products: int
    products_in_all_warehouses: int = Field(
        description="Products available in all warehouses (full distribution)"
    )
    products_in_single_warehouse: int = Field(
        description="Products only in one warehouse (single point of failure)"
    )
    products_unavailable: int = Field(
        description="Products not in any warehouse"
    )
    average_warehouses_per_product: float = Field(
        description="Average number of warehouses per product"
    )
    coverage_percentage: float = Field(
        description="Percentage of products that are available somewhere",
    )
