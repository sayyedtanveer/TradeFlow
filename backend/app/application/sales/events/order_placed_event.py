"""Order Placed domain event definition."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import List

from backend.app.domain.shared.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class OrderLineItem:
    """Lightweight representation of an order line for the event payload."""

    line_id: uuid.UUID
    product_id: uuid.UUID
    product_type: str
    uom_id: uuid.UUID
    quantity: float


@dataclass(frozen=True, kw_only=True)
class OrderPlacedEvent(DomainEvent):
    """
    Raised when a client places an order.

    Triggers the InventoryValidationHandler to check stock across warehouses
    and determine assignment or cancellation.

    Event type: order.placed
    """

    event_type: str = field(default="order.placed", init=False)
    order_id: uuid.UUID
    order_number: str
    client_id: uuid.UUID
    lines: List[OrderLineItem] = field(default_factory=list)
