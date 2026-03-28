/**
 * Supplier portal implementation contract placeholder.
 */

export const SUPPLIER_PORTAL_PROFILE_PAGE_CONTRACT = {
  filePath: "frontend/src/modules/procurement/pages/SupplierPortalProfilePage.tsx",
  exportName: "SupplierPortalProfilePage",
  routePath: "/supplier-portal/profile",
  serviceMethods: [
    "getSupplierProfile",
    "updateSupplierProfile",
  ],
  types: [
    "SupplierProfile",
    "SupplierProfileUpdateInput",
  ],
} as const;