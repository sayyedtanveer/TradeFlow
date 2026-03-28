/**
 * Supplier portal service contract placeholder.
 *
 * Declares the route names, payload shapes, and exported method names expected
 * for supplier self-service integration. This file is intentionally non-runtime.
 */

export const SUPPLIER_PORTAL_API_PREFIX = "/supplier" as const;

export const supplierPortalServiceContract = {
  filePath: "frontend/src/services/supplierPortalService.ts",
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