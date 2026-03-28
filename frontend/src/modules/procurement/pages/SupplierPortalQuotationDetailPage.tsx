/**
 * Supplier portal implementation contract placeholder.
 */

export const SUPPLIER_PORTAL_QUOTATION_DETAIL_PAGE_CONTRACT = {
  filePath: "frontend/src/modules/procurement/pages/SupplierPortalQuotationDetailPage.tsx",
  exportName: "SupplierPortalQuotationDetailPage",
  routePath: "/supplier-portal/quotations/:quotationId",
  serviceMethods: [
    "getSupplierQuotation",
    "updateSupplierQuotation",
  ],
  routeParams: ["quotationId"],
  types: [
    "SupplierQuotation",
    "SupplierQuotationUpdateInput",
  ],
} as const;