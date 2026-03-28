/**
 * Supplier portal implementation contract placeholder.
 */

export const SUPPLIER_PORTAL_INVOICES_PAGE_CONTRACT = {
  filePath: "frontend/src/modules/procurement/pages/SupplierPortalInvoicesPage.tsx",
  exportName: "SupplierPortalInvoicesPage",
  routePath: "/supplier-portal/invoices",
  serviceMethods: [
    "getSupplierInvoices",
    "getSupplierInvoice",
    "downloadSupplierInvoicePdf",
  ],
  types: [
    "SupplierInvoiceListItem",
    "SupplierInvoiceDetail",
  ],
} as const;