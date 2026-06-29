"""Sales domain module.

Contains all domain logic for sales order management:
- Entities: Client, SalesOrder, SalesOrderLine, PriceList
- Value Objects: OrderNumber, OrderStatus, PaymentStatus, LineStatus, Money
- Services: Pricing, Credit Validation, Inventory Reservation
- Repositories: ClientRepository, SalesOrderRepository, PriceListRepository
"""

from backend.app.domain.sales.entities import (
    Client,
    SalesOrder,
    SalesOrderLine,
    PriceList,
    PriceListLine,
)

from backend.app.domain.sales.value_objects import (
    OrderNumber,
    OrderStatus,
    PaymentStatus,
    LineStatus,
    Money,
)

from backend.app.domain.sales.services import (
    PricingService,
    CreditValidationService,
    InventoryReservationService,
    InsufficientInventoryError,
    OrderStateMachine,
    InvalidTransitionError,
)

from backend.app.domain.sales.repositories import (
    ClientRepository,
    SalesOrderRepository,
    PriceListRepository,
)

__all__ = [
    # Entities
    "Client",
    "SalesOrder",
    "SalesOrderLine",
    "PriceList",
    "PriceListLine",
    # Value Objects
    "OrderNumber",
    "OrderStatus",
    "PaymentStatus",
    "LineStatus",
    "Money",
    # Services
    "PricingService",
    "CreditValidationService",
    "InventoryReservationService",
    "InsufficientInventoryError",
    "OrderStateMachine",
    "InvalidTransitionError",
    # Repositories
    "ClientRepository",
    "SalesOrderRepository",
    "PriceListRepository",
]


