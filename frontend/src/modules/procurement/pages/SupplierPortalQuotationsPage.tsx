/**
 * Supplier portal implementation contract placeholder.
 *
 * This file documents the intended page/component name so other agents can
 * integrate consistently. It intentionally contains no runtime implementation.
 */

export const SUPPLIER_PORTAL_QUOTATIONS_PAGE_CONTRACT = {
  filePath: "frontend/src/modules/procurement/pages/SupplierPortalQuotationsPage.tsx",
  exportName: "SupplierPortalQuotationsPage",
  routePath: "/supplier-portal/quotations",
  serviceMethods: [
    "getSupplierQuotations",
    "createSupplierQuotation",
  ],
  types: [
    "SupplierQuotation",
    "SupplierQuotationCreateInput",
  ],
} as const;