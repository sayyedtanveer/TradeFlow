/**
 * Supplier portal service contract placeholder.
 *
 * Declares the route names, payload shapes, and exported method names expected
 * for supplier self-service integration. This file is intentionally non-runtime.
 */
/*
 NOTE (architect):
 - This file is a static contract/descriptor for the supplier-portal API surface
   used for documentation, discoverability, and potential codegen.
 - Do NOT assume this module is imported at runtime; keep the shape stable.
 - Minimal changes only: prefer adding comments here instead of changing keys.
 - TODO: Consider generating this from OpenAPI in the future to avoid drift.
*/

export const SUPPLIER_PORTAL_API_PREFIX = "/supplier" as const;
// Resolve contract file path at runtime (best-effort). Bundlers expose `import.meta.url`.
// Fallback to the static path string when resolution is not available.
const CONTRACT_FILE_PATH = (() => {
  try {
    // Vite/Rollup provide import.meta.url; convert to repo-relative path where possible.
    const url = new URL(import.meta.url)
    const pathname = url.pathname
    // If running from a developer machine, try to return a repo-relative path fragment.
    const marker = "/source/repos/"
    const idx = pathname.indexOf(marker)
    if (idx !== -1) return pathname.slice(idx + 1)
    return pathname
  } catch (e) {
    return "frontend/src/services/supplierPortalService.ts"
  }
})()

export const supplierPortalServiceContract = {
  filePath: CONTRACT_FILE_PATH,
  apiPrefix: SUPPLIER_PORTAL_API_PREFIX,
  methods: {
    getSupplierPurchaseOrders: {
      method: "GET",
      path: "/supplier/purchase-orders",
      returns: "Promise<SupplierPurchaseOrderListItem[]>",
    },
    getSupplierPurchaseOrder: {
      method: "GET",
      path: "/supplier/purchase-orders/:poId",
      returns: "Promise<SupplierPurchaseOrderDetail>",
    },
    acknowledgeSupplierPurchaseOrder: {
      method: "PUT",
      path: "/supplier/purchase-orders/:poId/acknowledge",
      returns: 'Promise<{ status: string }>',
    },
    createSupplierQuotation: {
      method: "POST",
      path: "/supplier/quotations",
      body: "SupplierQuotationCreateInput",
      returns: 'Promise<{ id: string }>',
    },
    getSupplierQuotations: {
      method: "GET",
      path: "/supplier/quotations",
      returns: "Promise<SupplierQuotation[]>",
    },
    getSupplierQuotation: {
      method: "GET",
      path: "/supplier/quotations/:quotationId",
      returns: "Promise<SupplierQuotation>",
    },
    updateSupplierQuotation: {
      method: "PUT",
      path: "/supplier/quotations/:quotationId",
      body: "SupplierQuotationUpdateInput",
      returns: 'Promise<{ status: string }>',
    },
    getSupplierProfile: {
      method: "GET",
      path: "/supplier/profile",
      returns: "Promise<SupplierProfile>",
    },
    updateSupplierProfile: {
      method: "PUT",
      path: "/supplier/profile",
      body: "SupplierProfileUpdateInput",
      returns: "Promise<SupplierProfile>",
    },
    getSupplierInvoices: {
      method: "GET",
      path: "/supplier/invoices",
      returns: "Promise<SupplierInvoiceListItem[]>",
    },
    createSupplierInvoice: {
      method: "POST",
      path: "/supplier/invoices",
      body: "SupplierInvoiceCreateInput",
      returns: 'Promise<{ id: string }>',
    },
    getSupplierInvoice: {
      method: "GET",
      path: "/supplier/invoices/:invoiceId",
      returns: "Promise<SupplierInvoiceDetail>",
    },
    downloadSupplierInvoicePdf: {
      method: "GET",
      path: "/supplier/invoices/:invoiceId/pdf",
      returns: "Promise<Blob | string>",
    },
    getSupplierPayments: {
      method: "GET",
      path: "/supplier/payments",
      returns: "Promise<SupplierPaymentListItem[]>",
    },
  },
} as const;