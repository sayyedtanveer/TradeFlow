/**
 * Supplier portal implementation contract placeholder.
 */

export const SUPPLIER_PORTAL_INVOICE_CREATE_PAGE_CONTRACT = {
  filePath: "frontend/src/modules/procurement/pages/SupplierPortalInvoiceCreatePage.tsx",
  exportName: "SupplierPortalInvoiceCreatePage",
  routePath: "/supplier-portal/invoices/new",
  serviceMethods: [
    "createSupplierInvoice",
    "getSupplierPurchaseOrders",
  ],
  types: [
    "SupplierInvoiceCreateInput",
    "SupplierPurchaseOrderListItem",
  ],
} as const;