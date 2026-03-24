from __future__ import annotations

from enum import Enum
from typing import FrozenSet, Dict


class Permission(str, Enum):
    """
    Fine-grained permissions using {module}:{action} convention.
    Add new permissions here as new modules are implemented.
    """

    # ── Wildcard ──────────────────────────────────────────────────────────
    ALL = "*"

    # ── Tenant / Users ────────────────────────────────────────────────────
    TENANT_READ = "tenant:read"
    TENANT_WRITE = "tenant:write"
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_INVITE = "user:invite"

    # ── Inventory ─────────────────────────────────────────────────────────
    INVENTORY_READ = "inventory:read"
    INVENTORY_WRITE = "inventory:write"
    INVENTORY_DELETE = "inventory:delete"

    # ── Sales ─────────────────────────────────────────────────────────────
    SALES_READ = "sales:read"
    SALES_WRITE = "sales:write"
    SALES_DELETE = "sales:delete"

    # ── Manufacturing ─────────────────────────────────────────────────────
    MANUFACTURING_READ = "manufacturing:read"
    MANUFACTURING_WRITE = "manufacturing:write"

    # ── Procurement ───────────────────────────────────────────────────────
    PROCUREMENT_READ = "procurement:read"
    PROCUREMENT_WRITE = "procurement:write"

    # ── Finance ───────────────────────────────────────────────────────────
    FINANCE_READ = "finance:read"
    FINANCE_WRITE = "finance:write"

    # ── Quality ───────────────────────────────────────────────────────────
    QUALITY_READ = "quality:read"
    QUALITY_WRITE = "quality:write"

    # ── Reports ───────────────────────────────────────────────────────────
    REPORTS_READ = "reports:read"


# ── Role → Permissions mapping ────────────────────────────────────────────────
# Import Role here would create circular deps, so we use string keys.
ROLE_PERMISSIONS: Dict[str, FrozenSet[str]] = {
    "admin": frozenset({Permission.ALL}),
    "manager": frozenset({
        Permission.TENANT_READ,
        Permission.USER_READ,
        Permission.INVENTORY_READ,
        Permission.INVENTORY_WRITE,
        Permission.SALES_READ,
        Permission.SALES_WRITE,
        Permission.MANUFACTURING_READ,
        Permission.MANUFACTURING_WRITE,
        Permission.PROCUREMENT_READ,
        Permission.PROCUREMENT_WRITE,
        Permission.FINANCE_READ,
        Permission.QUALITY_READ,
        Permission.QUALITY_WRITE,
        Permission.REPORTS_READ,
    }),
    "operator": frozenset({
        Permission.INVENTORY_READ,
        Permission.INVENTORY_WRITE,
        Permission.MANUFACTURING_READ,
        Permission.MANUFACTURING_WRITE,
        Permission.QUALITY_READ,
        Permission.QUALITY_WRITE,
    }),
    "viewer": frozenset({
        Permission.INVENTORY_READ,
        Permission.SALES_READ,
        Permission.MANUFACTURING_READ,
        Permission.PROCUREMENT_READ,
        Permission.FINANCE_READ,
        Permission.QUALITY_READ,
        Permission.REPORTS_READ,
    }),
}


def has_permission(role: str, permission: str) -> bool:
    """Return True if the given role grants the requested permission."""
    perms = ROLE_PERMISSIONS.get(role.lower(), frozenset())
    return Permission.ALL in perms or permission in perms
