import {
  ROLE_DASHBOARD_PATHS,
  ROLE_MODULE_ACCESS as ACTIVE_ROLE_MODULE_ACCESS,
  UserRole,
  hasModuleAccess as hasActiveModuleAccess,
  type AppModuleKey,
} from "@/lib/roles.config"

export { ROLE_DASHBOARD_PATHS, UserRole }

export enum AppModule {
  DASHBOARD = "dashboard",
  SYSTEM_MAP = "systemMap",
  PRODUCTS = "products",
  BOM = "bom",
  MANUFACTURING = "manufacturing",
  INVENTORY = "inventory",
  SALES = "sales",
  WORK_ORDERS = "workOrders",
  PROCUREMENT = "procurement",
  QUALITY = "quality",
  FINANCE = "finance",
  SHOP_FLOOR = "shopFloor",
  REPORTS = "reports",
  AUDIT_LOGS = "auditLogs",
  USERS = "users",
  SETTINGS = "settings",
  SUPPLIER_PORTAL = "supplierPortal",
}

export const ROLE_MODULE_ACCESS: Record<UserRole, AppModule[]> = Object.fromEntries(
  Object.entries(ACTIVE_ROLE_MODULE_ACCESS).map(([role, modules]) => [role, modules as AppModule[]])
) as Record<UserRole, AppModule[]>

export const hasModuleAccess = (role: UserRole | string, module: AppModule): boolean => {
  return hasActiveModuleAccess(role, module as AppModuleKey)
}
