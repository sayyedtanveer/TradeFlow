"""Warehouse Aggregate Root."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from backend.app.domain.shared.base_entity import AggregateRoot
from backend.app.domain.warehouse.value_objects import Address


class Warehouse(AggregateRoot):
    """
    Warehouse - Aggregate Root for warehouse management.

    Responsibilities:
    - Warehouse profile management (name, address, contact info)
    - Activation/deactivation lifecycle
    - Business rule enforcement (name length, uniqueness per tenant)
    """

    MAX_NAME_LENGTH = 100

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        name: str,
        address: Address,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        is_deleted: bool = False,
        deleted_at: Optional[datetime] = None,
    ) -> None:
        """Initialize Warehouse aggregate root."""
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            created_at=created_at,
            updated_at=updated_at,
            is_deleted=is_deleted,
            deleted_at=deleted_at,
        )
        self._name = name
        self._address = address
        self._phone = phone
        self._email = email
        self._is_active = is_active

        self._validate()

    def _validate(self) -> None:
        """Validate warehouse invariants."""
        if not self._name or not self._name.strip():
            raise ValueError("Warehouse name is required")
        if len(self._name) > self.MAX_NAME_LENGTH:
            raise ValueError(
                f"Warehouse name must not exceed {self.MAX_NAME_LENGTH} characters"
            )

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("Warehouse name is required")
        if len(value) > self.MAX_NAME_LENGTH:
            raise ValueError(
                f"Warehouse name must not exceed {self.MAX_NAME_LENGTH} characters"
            )
        self._name = value
        self._touch()

    @property
    def address(self) -> Address:
        return self._address

    @address.setter
    def address(self, value: Address) -> None:
        self._address = value
        self._touch()

    @property
    def phone(self) -> Optional[str]:
        return self._phone

    @phone.setter
    def phone(self, value: Optional[str]) -> None:
        self._phone = value
        self._touch()

    @property
    def email(self) -> Optional[str]:
        return self._email

    @email.setter
    def email(self, value: Optional[str]) -> None:
        self._email = value
        self._touch()

    @property
    def is_active(self) -> bool:
        return self._is_active

    # ── Domain Operations ─────────────────────────────────────────────────

    def deactivate(self) -> None:
        """Deactivate the warehouse. Prevents new order assignments."""
        if not self._is_active:
            raise ValueError("Warehouse is already inactive")
        self._is_active = False
        self._touch()

    def activate(self) -> None:
        """Reactivate a deactivated warehouse."""
        if self._is_active:
            raise ValueError("Warehouse is already active")
        self._is_active = True
        self._touch()

    def update(
        self,
        name: Optional[str] = None,
        address: Optional[Address] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
    ) -> None:
        """Update warehouse profile fields."""
        if name is not None:
            self.name = name
        if address is not None:
            self.address = address
        if phone is not None:
            self._phone = phone
        if email is not None:
            self._email = email
        self._touch()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "name": self._name,
            "address": self._address.to_dict(),
            "phone": self._phone,
            "email": self._email,
            "is_active": self._is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
