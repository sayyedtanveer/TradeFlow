export enum UserRole {
  ADMIN = 'ADMIN',
  TENANT_ADMIN = 'TENANT_ADMIN',
  PLANNER = 'PLANNER',
  STOREKEEPER = 'STOREKEEPER',
  SALES = 'SALES',
  QC = 'QC',
  WORKER = 'WORKER',
  CLIENT = 'CLIENT',
}

// Module IDs correspond to route paths or main sections
export enum AppModule {
  DASHBOARD = 'DASHBOARD',
  PRODUCTS = 'PRODUCTS',
  BOM = 'BOM',
  OPERATIONS = 'OPERATIONS',
  WORKSTATIONS = 'WORKSTATIONS',
  INVENTORY = 'INVENTORY',
  SALES = 'SALES',
  WORK_ORDERS = 'WORK_ORDERS',
  QUALITY_CHECKS = 'QUALITY_CHECKS',
  SHOP_FLOOR = 'SHOP_FLOOR',
  REPORTS = 'REPORTS',
}

export const ROLE_DASHBOARD_PATHS: Record<UserRole, string> = {
  [UserRole.ADMIN]: '/dashboard',
  [UserRole.TENANT_ADMIN]: '/dashboard',
  [UserRole.PLANNER]: '/dashboard/planner',
  [UserRole.STOREKEEPER]: '/dashboard/storekeeper',
  [UserRole.SALES]: '/dashboard/sales',
  [UserRole.QC]: '/dashboard/qc',
  [UserRole.WORKER]: '/shop-floor',
  [UserRole.CLIENT]: '/dashboard/client',
};

export const ROLE_MODULE_ACCESS: Record<UserRole, AppModule[]> = {
  [UserRole.ADMIN]: Object.values(AppModule),
  [UserRole.TENANT_ADMIN]: Object.values(AppModule),
  [UserRole.PLANNER]: [
    AppModule.DASHBOARD,
    AppModule.BOM,
    AppModule.WORK_ORDERS,
    AppModule.INVENTORY, // read-only context handled in UI
  ],
  [UserRole.STOREKEEPER]: [
    AppModule.DASHBOARD,
    AppModule.INVENTORY,
    AppModule.WORK_ORDERS,
  ],
  [UserRole.SALES]: [
    AppModule.DASHBOARD,
    AppModule.SALES,
  ],
  [UserRole.QC]: [
    AppModule.DASHBOARD,
    AppModule.QUALITY_CHECKS,
    AppModule.WORK_ORDERS,
  ],
  [UserRole.WORKER]: [
    AppModule.SHOP_FLOOR,
  ],
  [UserRole.CLIENT]: [
    AppModule.DASHBOARD,
    AppModule.SALES, // Restricted view applied in UI
  ],
};

export const hasModuleAccess = (role: UserRole | string, module: AppModule): boolean => {
  const normalizedRole = role.toUpperCase() as UserRole;
  const accessList = ROLE_MODULE_ACCESS[normalizedRole] || [];
  return accessList.includes(module);
};
