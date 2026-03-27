"""Client Entity - Core domain entity for sales."""

from decimal import Decimal
from uuid import UUID

from backend.app.domain.shared.base_entity import AggregateRoot


class Client(AggregateRoot):
    """
    Client aggregate root.
    
    Core responsibilities:
    - Track credit limits and usage
    - Maintain client contact info and settings
    - Support credit lifecycle (check, allocate, release)
    """

    def __init__(
        self,
        id: UUID,
        tenant_id: UUID,
        code: str,
        name: str,
        email: str,
        phone: str | None = None,
        address: str | None = None,
        city: str | None = None,
        state: str | None = None,
        country: str | None = None,
        postal_code: str | None = None,
        gst: str | None = None,
        payment_terms_days: int = 30,
        credit_limit: Decimal = Decimal("0"),
        is_active: bool = True,
    ):
        """Initialize Client."""
        super().__init__(id=id, tenant_id=tenant_id)

        self.code = code
        self.name = name
        self.email = email
        self.phone = phone
        self.address = address
        self.city = city
        self.state = state
        self.country = country
        self.postal_code = postal_code
        self.gst = gst
        self.payment_terms_days = payment_terms_days
        self.credit_limit = Decimal(str(credit_limit))
        self.credit_used = Decimal("0")
        self.is_active = is_active

        self._validate()

    def _validate(self) -> None:
        """Validate invariants."""
        if not self.code or not self.code.strip():
            raise ValueError("Client code is required")
        if not self.name or not self.name.strip():
            raise ValueError("Client name is required")
        if not self.email or "@" not in self.email:
            raise ValueError("Valid email is required")
        if self.credit_limit < 0:
            raise ValueError("Credit limit cannot be negative")
        if self.credit_used < 0:
            raise ValueError("Credit used cannot be negative")
        if self.credit_used > self.credit_limit:
            raise ValueError("Credit used cannot exceed credit limit")

    def check_available_credit(self, amount: Decimal) -> bool:
        """
        Check if client has sufficient available credit.
        
        Args:
            amount: Amount to check
            
        Returns:
            True if amount <= (credit_limit - credit_used)
        """
        available = self.credit_limit - self.credit_used
        return amount <= available

    def increase_credit_used(self, amount: Decimal) -> None:
        """
        Increase credit used for order confirmation.
        
        Args:
            amount: Amount to allocate
            
        Raises:
            ValueError: If would exceed credit limit
        """
        amount = Decimal(str(amount))
        if amount < 0:
            raise ValueError("Amount cannot be negative")

        new_total = self.credit_used + amount
        if new_total > self.credit_limit:
            raise ValueError(
                f"Credit allocation would exceed limit: "
                f"{new_total} > {self.credit_limit}"
            )

        self.credit_used = new_total

    def decrease_credit_used(self, amount: Decimal) -> None:
        """
        Decrease credit used (for order cancellation or payment).
        
        Args:
            amount: Amount to release
            
        Raises:
            ValueError: If would go negative
        """
        amount = Decimal(str(amount))
        if amount < 0:
            raise ValueError("Amount cannot be negative")

        new_total = self.credit_used - amount
        if new_total < 0:
            raise ValueError(
                f"Cannot release {amount}: would make credit_used negative"
            )

        self.credit_used = new_total

    def deactivate(self) -> None:
        """Deactivate client (soft delete alternative)."""
        self.is_active = False

    def reactivate(self) -> None:
        """Reactivate client."""
        self.is_active = True

