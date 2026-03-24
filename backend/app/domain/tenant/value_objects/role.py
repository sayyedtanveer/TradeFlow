from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    """
    User role within a tenant.

    Permissions for each role are defined in domain/shared/permissions.py.
    """

    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "Role":
        try:
            return cls(value.lower())
        except ValueError:
            valid = [r.value for r in cls]
            raise ValueError(f"Invalid role '{value}'. Must be one of: {valid}")
