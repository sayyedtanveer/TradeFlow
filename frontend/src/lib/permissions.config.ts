/**
 * Mirrors backend/app/domain/shared/permissions.py ROLE_PERMISSIONS + has_permission.
 * Use hasPermission(userRole, permission) — no hardcoded role checks in UI.
 */

export const Permission = {
  ALL: "*",
  TENANT_READ: "tenant:read",
  TENANT_WRITE: "tenant:write",
  USER_READ: "user:read",
  USER_WRITE: "user:write",
  INVENTORY_READ: "inventory:read",
  INVENTORY_WRITE: "inventory:write",
  INVENTORY_DELETE: "inventory:delete",
  SALES_READ: "sales:read",
  SALES_WRITE: "sales:write",
  MANUFACTURING_READ: "manufacturing:read",
  MANUFACTURING_WRITE: "manufacturing:write",
  PROCUREMENT_READ: "procurement:read",
  PROCUREMENT_WRITE: "procurement:write",
  FINANCE_READ: "finance:read",
  FINANCE_WRITE: "finance:write",
  QUALITY_READ: "quality:read",
  QUALITY_WRITE: "quality:write",
  REPORTS_READ: "reports:read",
} as const

export type PermissionString = (typeof Permission)[keyof typeof Permission]

const _mfgInvQuality = new Set<string>([
  Permission.INVENTORY_READ,
  Permission.INVENTORY_WRITE,
  Permission.MANUFACTURING_READ,
  Permission.MANUFACTURING_WRITE,
  Permission.QUALITY_READ,
  Permission.QUALITY_WRITE,
])

const ROLE_PERMISSIONS: Record<string, Set<string>> = {
  admin: new Set([Permission.ALL]),
  tenant_admin: new Set([Permission.ALL]),
  manager: new Set([
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
  ]),
  operator: new Set([
    ..._mfgInvQuality,
    Permission.PROCUREMENT_READ,
    Permission.PROCUREMENT_WRITE,
  ]),
  storekeeper: new Set([
    ..._mfgInvQuality,
    Permission.PROCUREMENT_READ,
    Permission.PROCUREMENT_WRITE,
  ]),
  planner: new Set([
    Permission.INVENTORY_READ,
    Permission.MANUFACTURING_READ,
    Permission.MANUFACTURING_WRITE,
    Permission.PROCUREMENT_READ,
    Permission.PROCUREMENT_WRITE,
    Permission.QUALITY_READ,
    Permission.REPORTS_READ,
  ]),
  qc: new Set([
    Permission.INVENTORY_READ,
    Permission.INVENTORY_WRITE,
    Permission.QUALITY_READ,
    Permission.QUALITY_WRITE,
    Permission.PROCUREMENT_READ,
  ]),
  sales: new Set([
    Permission.INVENTORY_READ,
    Permission.SALES_READ,
    Permission.SALES_WRITE,
    Permission.MANUFACTURING_READ,
    Permission.REPORTS_READ,
  ]),
  worker: new Set([
    Permission.MANUFACTURING_READ,
    Permission.MANUFACTURING_WRITE,
    Permission.INVENTORY_READ,
  ]),
  client: new Set([Permission.SALES_READ, Permission.INVENTORY_READ]),
  supplier: new Set([Permission.PROCUREMENT_READ, Permission.PROCUREMENT_WRITE]),
  viewer: new Set([
    Permission.INVENTORY_READ,
    Permission.SALES_READ,
    Permission.MANUFACTURING_READ,
    Permission.PROCUREMENT_READ,
    Permission.FINANCE_READ,
    Permission.QUALITY_READ,
    Permission.REPORTS_READ,
  ]),
}

export function hasPermission(roleRaw: string | undefined, permission: string): boolean {
  if (!roleRaw) return false
  const role = roleRaw.toLowerCase().trim()
  const perms = ROLE_PERMISSIONS[role]
  if (!perms) return false
  return perms.has(Permission.ALL) || perms.has(permission)
}
