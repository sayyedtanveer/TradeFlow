"""API Schemas for Order Management (Admin)."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal
import uuid
from datetime import date, datetime


# ── Request Schemas ───────────────────────────────────────────────────────────

class OrderLineItemRequest(BaseModel):
    """Order line item for allocation."""
    product_id: uuid.UUID
    quantity: int = Field(..., gt=0, description="Quantity to order")


class AllocateOrderRequest(BaseModel):
    """Request to auto-allocate an order."""
    line_items: List[OrderLineItemRequest] = Field(
        ...,
        description="Line items in order",
        min_items=1,
    )
    exclude_warehouses: List[uuid.UUID] = Field(
        default_factory=list,
        description="Warehouses to skip (e.g., already tried)",
    )


class AssignOrderToWarehouseRequest(BaseModel):
    """Request to manually assign order to warehouse."""
    warehouse_id: uuid.UUID = Field(..., description="Warehouse to assign to")


class ReassignOrderToWarehouseRequest(BaseModel):
    """Request to reassign order to different warehouse."""
    warehouse_id: uuid.UUID = Field(..., description="New warehouse")
    reason: str = Field(..., description="Reason for reassignment")


# ── Response Schemas ──────────────────────────────────────────────────────────

class OrderLineItemResponse(BaseModel):
    """Order line item in response."""
    product_id: str
    product_name: Optional[str] = None
    product_code: Optional[str] = None
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class OrderAllocationResponse(BaseModel):
    """Response for order allocation."""
    order_id: str
    allocated_warehouse_id: str
    warehouse_name: Optional[str] = None
    status: str
    message: str
    allocated_at: Optional[datetime] = None


class AdminOrderResponse(BaseModel):
    """Admin view of sales order with allocation info."""
    id: str
    order_number: str
    client_id: str
    client_name: Optional[str] = None
    order_date: date
    delivery_date: date
    status: str
    payment_status: str
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    grand_total: Decimal
    notes: Optional[str] = None
    
    # Allocation fields
    assigned_warehouse_id: Optional[str] = None
    assigned_warehouse_name: Optional[str] = None
    assigned_at: Optional[datetime] = None
    
    # Line items
    line_items: List[OrderLineItemResponse] = Field(default_factory=list)
    
    # Audit
    created_at: datetime
    updated_at: datetime


class AdminOrderListResponse(BaseModel):
    """Admin list view of sales orders."""
    id: str
    order_number: str
    client_name: Optional[str] = None
    order_date: date
    delivery_date: date
    status: str
    payment_status: str
    grand_total: Decimal
    assigned_warehouse_id: Optional[str] = None
    assigned_warehouse_name: Optional[str] = None
    created_at: datetime


class OrderAllocationStatsResponse(BaseModel):
    """Statistics on order allocation."""
    total_orders: int
    allocated_orders: int
    unallocated_orders: int
    allocation_rate: float = Field(description="Percentage of allocated orders")
    orders_by_warehouse: dict = Field(
        description="Count of orders per warehouse",
        default_factory=dict,
    )
