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
    RBAC_READ = "rbac:read"
    RBAC_WRITE = "rbac:write"
    ADMIN_READ = "admin:read"
    AUDIT_READ = "audit:read"

    # ── Inventory ─────────────────────────────────────────────────────────
    INVENTORY_READ = "inventory:read"
    INVENTORY_WRITE = "inventory:write"
    INVENTORY_DELETE = "inventory:delete"

    # ── Sales ─────────────────────────────────────────────────────────────
    SALES_READ = "sales:read"
    SALES_WRITE = "sales:write"
    SALES_DELETE = "sales:delete"
    SALES_VIEW_ORDERS = "sales:view_orders"
    SALES_CREATE_ORDER = "sales:create_order"
    SALES_APPROVE_ORDER = "sales:approve_order"

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

    # Portal / dashboard scopes
    CLIENT_READ = "client:read"
    SUPPLIER_READ = "supplier:read"
    SUPPLIER_WRITE = "supplier:write"
    STOREKEEPER_READ = "storekeeper:read"
    WORKER_READ = "worker:read"
    DOCUMENTS_READ = "documents:read"
    DOCUMENTS_WRITE = "documents:write"


# ── Role → Permissions mapping ────────────────────────────────────────────────
# Import Role here would create circular deps, so we use string keys.
_mfg_inv_quality = frozenset({
    Permission.INVENTORY_READ,
    Permission.INVENTORY_WRITE,
    Permission.MANUFACTURING_READ,
    Permission.MANUFACTURING_WRITE,
    Permission.QUALITY_READ,
    Permission.QUALITY_WRITE,
})

ROLE_PERMISSIONS: Dict[str, FrozenSet[str]] = {
    "admin": frozenset({Permission.ALL}),
    "tenant_admin": frozenset({Permission.ALL}),
    "manager": frozenset({
        Permission.ADMIN_READ,
        Permission.RBAC_READ,
        Permission.TENANT_READ,
        Permission.USER_READ,
        Permission.INVENTORY_READ,
        Permission.INVENTORY_WRITE,
        Permission.SALES_READ,
        Permission.SALES_WRITE,
        Permission.SALES_VIEW_ORDERS,
        Permission.SALES_CREATE_ORDER,
        Permission.SALES_APPROVE_ORDER,
        Permission.MANUFACTURING_READ,
        Permission.MANUFACTURING_WRITE,
        Permission.PROCUREMENT_READ,
        Permission.PROCUREMENT_WRITE,
        Permission.FINANCE_READ,
        Permission.QUALITY_READ,
        Permission.QUALITY_WRITE,
        Permission.REPORTS_READ,
        Permission.STOREKEEPER_READ,
        Permission.WORKER_READ,
    }),
    # Shop / warehouse: inventory + manufacturing + procurement (GRN, subcontract) + quality execution
    "operator": frozenset(
        _mfg_inv_quality
        | {
            Permission.PROCUREMENT_READ,
            Permission.PROCUREMENT_WRITE,
            Permission.STOREKEEPER_READ,
        }
    ),
    "storekeeper": frozenset(
        _mfg_inv_quality
        | {
            Permission.PROCUREMENT_READ,
            Permission.PROCUREMENT_WRITE,
            Permission.STOREKEEPER_READ,
        }
    ),
    "planner": frozenset({
        Permission.INVENTORY_READ,
        Permission.MANUFACTURING_READ,
        Permission.MANUFACTURING_WRITE,
        Permission.PROCUREMENT_READ,
        Permission.PROCUREMENT_WRITE,
        Permission.QUALITY_READ,
        Permission.REPORTS_READ,
        Permission.STOREKEEPER_READ,
    }),
    "qc": frozenset({
        Permission.INVENTORY_READ,
        Permission.QUALITY_READ,
        Permission.QUALITY_WRITE,
        Permission.PROCUREMENT_READ,
    }),
    "sales": frozenset({
        Permission.INVENTORY_READ,
        Permission.SALES_READ,
        Permission.SALES_WRITE,
        Permission.SALES_VIEW_ORDERS,
        Permission.SALES_CREATE_ORDER,
        Permission.MANUFACTURING_READ,
        Permission.REPORTS_READ,
    }),
    "worker": frozenset({
        Permission.MANUFACTURING_READ,
        Permission.MANUFACTURING_WRITE,
        Permission.INVENTORY_READ,
        Permission.WORKER_READ,
    }),
    "client": frozenset({
        Permission.SALES_READ,
        Permission.SALES_VIEW_ORDERS,
        Permission.SALES_CREATE_ORDER,
        Permission.INVENTORY_READ,
        Permission.CLIENT_READ,
    }),
    "supplier": frozenset({
        Permission.PROCUREMENT_READ,
        Permission.PROCUREMENT_WRITE,
        Permission.SUPPLIER_READ,
        Permission.SUPPLIER_WRITE,
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
    perms = {
        granted.value if isinstance(granted, Permission) else str(granted)
        for granted in ROLE_PERMISSIONS.get(role.lower(), frozenset())
    }
    return Permission.ALL.value in perms or permission in perms
