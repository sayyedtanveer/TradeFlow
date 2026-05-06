import { apiClient } from "./api-client"

export interface Invoice {
  id: string
  invoice_number: string
  sales_order_id: string | null
  client_id: string
  client_name: string
  client_address?: string
  client_gst_number?: string
  status: "DRAFT" | "SENT" | "PARTIAL" | "PAID" | "OVERDUE" | "CANCELLED" | "VOID"
  invoice_date: string
  due_date: string
  subtotal: number
  discount_amount: number
  tax_amount: number
  grand_total: number
  paid_amount: number
  balance_due: number
  notes?: string
  terms?: string
  created_at: string
  lines: InvoiceLine[]
  payments: PaymentBrief[]
}

export interface InvoiceLine {
  id: string
  product_id: string
  product_type: string
  description?: string
  quantity: number
  unit_price: number
  discount_amount: number
  tax_rate: number
  tax_amount: number
  total: number
}

export interface PaymentBrief {
  id: string
  payment_number: string
  amount: number
  payment_date: string
  payment_method: string
}

export interface Payment {
  id: string
  payment_number: string
  invoice_id: string
  client_id: string
  amount: number
  payment_date: string
  payment_method: string
  reference_number?: string
  notes?: string
  created_at: string
}

export interface SupplierInvoice {
  id: string
  invoice_number: string
  supplier_invoice_ref?: string
  purchase_order_id?: string
  supplier_id: string
  supplier_name: string
  status: "PENDING" | "PARTIAL" | "PAID" | "OVERDUE" | "CANCELLED"
  invoice_date: string
  due_date: string
  subtotal: number
  tax_amount: number
  grand_total: number
  paid_amount: number
  balance_due: number
  notes?: string
  created_at: string
}

export interface FinanceDashboard {
  ar: {
    total_billed: number
    total_collected: number
    total_outstanding: number
    open_count: number
  }
  ap: {
    total_payable: number
    total_paid: number
    outstanding: number
    open_count: number
  }
  revenue_trend: Array<{
    month: string
    invoice_count: number
    revenue: number
    collected: number
  }>
}

export interface ARAgingRow {
  client_id: string
  client_name: string
  current_amount: number
  overdue_1_30: number
  overdue_31_60: number
  overdue_61_90: number
  overdue_90_plus: number
  total_outstanding: number
}

export interface APAgingRow {
  supplier_id: string
  supplier_name: string
  current_amount: number
  overdue_1_30: number
  overdue_31_60: number
  overdue_61_90: number
  overdue_90_plus: number
  total_outstanding: number
}

export interface LedgerEntry {
  id: string
  reference_type: string
  reference_id: string
  account_type: string
  debit: number
  credit: number
  description: string
  created_at: string
}

export interface TrialBalanceEntry {
  code: string
  name: string
  account_type: string
  debit: number
  credit: number
  balance: number
}

export interface TrialBalanceReport {
  as_of: string
  items: TrialBalanceEntry[]
  totals: {
    debit: number
    credit: number
    is_balanced: boolean
  }
}

export interface ProfitAndLossReport {
  period: {
    from: string
    to: string
  }
  income: Array<{ code: string; name: string; amount: number }>
  expenses: Array<{ code: string; name: string; amount: number }>
  totals: {
    income: number
    expense: number
    net_profit: number
  }
}

export interface BalanceSheetReport {
  as_of: string
  assets: Array<{ code: string; name: string; amount: number }>
  liabilities: Array<{ code: string; name: string; amount: number }>
  equity: Array<{ code: string; name: string; amount: number }>
  totals: {
    assets: number
    liabilities: number
    equity: number
    liabilities_and_equity: number
    is_balanced: boolean
  }
}

export interface CashFlowReport {
  months: number
  items: Array<{ month: string; cash_in: number; cash_out: number }>
  totals: {
    cash_in: number
    cash_out: number
    net_cash_flow: number
  }
}

export interface FinanceSettings {
  tenant_id: string
  invoice_prefix: string
  supplier_invoice_prefix: string
  payment_prefix: string
  supplier_payment_prefix: string
  invoice_template: string
  default_tax_rate: number
  default_payment_terms_days: number
  gst_number?: string
  logo_url?: string
  custom_template: Record<string, unknown>
  ar_account_code: string
  bank_account_code: string
  ap_account_code: string
  revenue_account_code: string
  expense_account_code: string
  updated_at: string
}

export interface ChartOfAccount {
  id: string
  code: string
  name: string
  account_type: string
  category: string
  normal_balance: string
  is_system: boolean
  is_active: boolean
}

export interface Notification {
  id: string
  type: string
  title: string
  message: string
  reference_type?: string
  reference_id?: string
  is_read: boolean
  sent_at: string
}

const BASE = "/finance"
const REPORTS_BASE = "/reports"
const NOTIF_BASE = "/notifications"

async function downloadBlob(path: string, filename?: string) {
  const res = await apiClient.get(path, { responseType: "blob" })
  const blob = new Blob([res.data], { type: res.headers["content-type"] || "application/pdf" })
  const url = window.URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = filename || "download.pdf"
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.URL.revokeObjectURL(url)
}

export const financeService = {
  async createInvoiceFromSO(payload: {
    sales_order_id: string
    notes?: string
    terms?: string
  }): Promise<Invoice> {
    const res = await apiClient.post(`${BASE}/invoices/from-so`, payload)
    return res.data
  },

  async listInvoices(params?: {
    status?: string
    client_id?: string
    overdue_only?: boolean
    page?: number
    page_size?: number
  }) {
    const res = await apiClient.get(`${BASE}/invoices`, { params })
    return res.data as { items: Invoice[]; total: number; page: number; pages: number }
  },

  async getInvoice(id: string): Promise<Invoice> {
    const res = await apiClient.get(`${BASE}/invoices/${id}`)
    return res.data
  },

  async sendInvoice(id: string): Promise<Invoice> {
    const res = await apiClient.post(`${BASE}/invoices/${id}/send`)
    return res.data
  },

  async voidInvoice(id: string): Promise<Invoice> {
    const res = await apiClient.post(`${BASE}/invoices/${id}/void`)
    return res.data
  },

  async downloadInvoicePdf(id: string, invoiceNumber?: string) {
    await downloadBlob(`${BASE}/invoices/${id}/pdf`, `${invoiceNumber || id}.pdf`)
  },

  async recordPayment(payload: {
    invoice_id: string
    amount: number
    payment_date: string
    payment_method: string
    reference_number?: string
    notes?: string
  }): Promise<Payment> {
    const res = await apiClient.post(`${BASE}/payments`, payload)
    return res.data
  },

  async listPayments(params?: { invoice_id?: string; page?: number; page_size?: number }) {
    const res = await apiClient.get(`${BASE}/payments`, { params })
    return res.data as { items: Payment[]; total: number; page: number; pages: number }
  },

  async downloadReceiptPdf(id: string, paymentNumber?: string) {
    await downloadBlob(`${BASE}/payments/${id}/receipt-pdf`, `${paymentNumber || id}.pdf`)
  },

  async createSupplierInvoice(payload: {
    supplier_id: string
    purchase_order_id?: string
    supplier_invoice_ref?: string
    invoice_date: string
    due_date: string
    subtotal: number
    tax_amount?: number
    grand_total: number
    notes?: string
  }): Promise<SupplierInvoice> {
    const res = await apiClient.post(`${BASE}/supplier-invoices`, payload)
    return res.data
  },

  async listSupplierInvoices(params?: {
    status?: string
    supplier_id?: string
    page?: number
    page_size?: number
  }) {
    const res = await apiClient.get(`${BASE}/supplier-invoices`, { params })
    return res.data as { items: SupplierInvoice[]; total: number; page: number; pages: number }
  },

  async recordSupplierPayment(payload: {
    supplier_invoice_id: string
    amount: number
    payment_date: string
    payment_method: string
    reference_number?: string
    notes?: string
  }) {
    const res = await apiClient.post(`${BASE}/supplier-payments`, payload)
    return res.data
  },

  async getDashboard(): Promise<FinanceDashboard> {
    const res = await apiClient.get(`${BASE}/dashboard`)
    return res.data
  },

  async getARaging(): Promise<ARAgingRow[]> {
    const res = await apiClient.get(`${BASE}/ar-aging`)
    return res.data
  },

  async getAPAging(): Promise<APAgingRow[]> {
    const res = await apiClient.get(`${BASE}/ap-aging`)
    return res.data
  },

  async getLedger(params?: { reference_type?: string; page?: number; page_size?: number }) {
    const res = await apiClient.get(`${BASE}/ledger`, { params })
    return res.data as { items: LedgerEntry[]; total: number; page: number; pages: number }
  },

  async getTrialBalance(asOf?: string): Promise<TrialBalanceReport> {
    const res = await apiClient.get(`${BASE}/trial-balance`, { params: { as_of: asOf } })
    return res.data
  },

  async getProfitAndLoss(params?: { from_date?: string; to_date?: string }): Promise<ProfitAndLossReport> {
    const res = await apiClient.get(`${BASE}/profit-loss`, { params })
    return res.data
  },

  async getBalanceSheet(asOf?: string): Promise<BalanceSheetReport> {
    const res = await apiClient.get(`${BASE}/balance-sheet`, { params: { as_of: asOf } })
    return res.data
  },

  async getCashFlow(months = 6): Promise<CashFlowReport> {
    const res = await apiClient.get(`${BASE}/cash-flow`, { params: { months } })
    return res.data
  },

  async getFinanceSettings(): Promise<FinanceSettings> {
    const res = await apiClient.get(`${BASE}/settings`)
    return res.data
  },

  async updateFinanceSettings(payload: Partial<FinanceSettings>): Promise<FinanceSettings> {
    const res = await apiClient.put(`${BASE}/settings`, payload)
    return res.data
  },

  async getChartOfAccounts(): Promise<ChartOfAccount[]> {
    const res = await apiClient.get(`${BASE}/chart-of-accounts`)
    return res.data
  },

  async getInventorySummary() {
    const res = await apiClient.get(`${REPORTS_BASE}/inventory/summary`)
    return res.data
  },

  async getInventoryTurnover() {
    const res = await apiClient.get(`${REPORTS_BASE}/inventory/turnover`)
    return res.data
  },

  async getProductionSummary() {
    const res = await apiClient.get(`${REPORTS_BASE}/production/summary`)
    return res.data
  },

  async getProductionEfficiency() {
    const res = await apiClient.get(`${REPORTS_BASE}/production/efficiency`)
    return res.data
  },

  async getSalesSummary() {
    const res = await apiClient.get(`${REPORTS_BASE}/sales/summary`)
    return res.data
  },

  async getTopClients(limit = 10) {
    const res = await apiClient.get(`${REPORTS_BASE}/sales/top-clients`, { params: { limit } })
    return res.data
  },

  async getProcurementSummary() {
    const res = await apiClient.get(`${REPORTS_BASE}/procurement/summary`)
    return res.data
  },

  async getQualitySummary() {
    const res = await apiClient.get(`${REPORTS_BASE}/quality/summary`)
    return res.data
  },

  async getFinanceSummary() {
    const res = await apiClient.get(`${REPORTS_BASE}/finance/summary`)
    return res.data
  },

  async getFinanceAPAging() {
    const res = await apiClient.get(`${REPORTS_BASE}/finance/ap-aging`)
    return res.data
  },

  async getFinanceTrialBalance() {
    const res = await apiClient.get(`${REPORTS_BASE}/finance/trial-balance`)
    return res.data
  },

  async getFinanceProfitLoss() {
    const res = await apiClient.get(`${REPORTS_BASE}/finance/profit-loss`)
    return res.data
  },

  async getFinanceBalanceSheet() {
    const res = await apiClient.get(`${REPORTS_BASE}/finance/balance-sheet`)
    return res.data
  },

  async getFinanceCashFlow() {
    const res = await apiClient.get(`${REPORTS_BASE}/finance/cash-flow`)
    return res.data
  },

  async getNotifications(params?: { unread_only?: boolean; page?: number; page_size?: number }) {
    const res = await apiClient.get(`${NOTIF_BASE}/`, { params })
    return res.data as {
      items: Notification[]
      total: number
      unread_count: number
      page: number
      pages: number
    }
  },

  async markRead(id: string) {
    const res = await apiClient.post(`${NOTIF_BASE}/${id}/read`)
    return res.data
  },

  async markAllRead() {
    const res = await apiClient.post(`${NOTIF_BASE}/mark-all-read`)
    return res.data
  },
}
