"""Address Value Object for Warehouse domain."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Address:
    """
    Immutable address value object for warehouse locations.

    Equality is based on all field values, not identity.
    """

    street: str
    city: str
    region: str
    postal_code: str
    country: str

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        """Validate address fields."""
        if not self.street or not self.street.strip():
            raise ValueError("Street is required")
        if not self.city or not self.city.strip():
            raise ValueError("City is required")
        if not self.country or not self.country.strip():
            raise ValueError("Country is required")

    def to_dict(self) -> dict:
        """Serialize address to dictionary."""
        return {
            "street": self.street,
            "city": self.city,
            "region": self.region,
            "postal_code": self.postal_code,
            "country": self.country,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Address":
        """Create Address from dictionary."""
        return cls(
            street=data.get("street", ""),
            city=data.get("city", ""),
            region=data.get("region", ""),
            postal_code=data.get("postal_code", ""),
            country=data.get("country", ""),
        )
