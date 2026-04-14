import { apiClient } from "@/services/api-client"

export type TimelineStatus = "completed" | "current" | "upcoming" | "cancelled"

export interface ClientSessionResponse {
  access_token: string
  token_type: string
  user_id: string
  tenant_id: string
  client_id: string
  email: string
  role: string
  full_name: string
}

export interface ClientTimelineStep {
  label: string
  status: TimelineStatus
}

export interface ClientAvailability {
  source: string
  available_quantity: number | null
  status: "available" | "backorder" | "unknown"
  backorder_warning: boolean
  message: string
}

export interface ClientOrderLine {
  id: string
  product_id: string
  product_type: string
  product_name: string
  product_code?: string | null
  uom_id: string
  quantity: number
  unit_price: number
  tax_rate: number
  tax_amount: number
  line_total: number
  allocated_quantity: number
  shipped_quantity: number
  backorder_quantity: number
  status: string
  availability: ClientAvailability
}

export interface ClientOrder {
  id: string
  order_number: string
  client_id: string
  order_date: string
  delivery_date: string
  status: string
  payment_status: string
  subtotal: number
  discount_amount: number
  tax_amount: number
  grand_total: number
  notes?: string | null
  created_at: string
  updated_at: string
  timeline: ClientTimelineStep[]
  lines: ClientOrderLine[]
  line_count: number
  tracking: {
    estimated_delivery_date: string
    shipping_status: string
    tracking_reference?: string | null
    tracking_notes?: string
  }
  availability: ClientAvailability[]
  credit_warning?: boolean
}

export interface ClientInvoice {
  id: string
  invoice_number: string
  sales_order_id?: string | null
  client_id: string
  client_name: string
  client_address?: string | null
  client_gst_number?: string | null
  status: string
  invoice_date: string
  due_date: string
  subtotal: number
  discount_amount: number
  tax_amount: number
  grand_total: number
  paid_amount: number
  balance_due: number
  notes?: string | null
  terms?: string | null
  created_at: string
  payment_link: string
  lines: Array<{
    id: string
    product_id: string
    product_type: string
    description?: string | null
    quantity: number
    unit_price: number
    discount_amount: number
    tax_rate: number
    tax_amount: number
    total: number
  }>
  payments: Array<{
    id: string
    payment_number: string
    amount: number
    payment_date: string
    payment_method: string
  }>
}

export interface ClientCredit {
  client_id: string
  credit_limit: number | null
  credit_used: number
  credit_remaining: number | null
  usage_percent: number | null
  is_over_limit: boolean
  is_low_credit: boolean
}

export interface ClientAddress {
  id: string
  type: "billing" | "shipping"
  label?: string | null
  contact_name?: string | null
  address_line1: string
  address_line2?: string | null
  city?: string | null
  state?: string | null
  postal_code?: string | null
  country?: string | null
  phone?: string | null
  email?: string | null
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface ClientNotificationSettings {
  order_confirmed: boolean
  order_shipped: boolean
  order_delivered: boolean
  invoice_overdue: boolean
  low_credit: boolean
  marketing: boolean
}

export interface ClientNotification {
  id: string
  type: string
  title: string
  message: string
  reference_type?: string | null
  reference_id?: string | null
  is_read: boolean
  sent_at: string
}

export interface ClientProfile {
  company: {
    id: string
    code: string
    name: string
    email?: string | null
    phone?: string | null
    address?: string | null
    gst_number?: string | null
    payment_terms_days: number
    credit_limit: number | null
    credit_used: number
  }
  contact: {
    id: string
    first_name: string
    last_name: string
    email: string
  }
  addresses: ClientAddress[]
  notifications: ClientNotificationSettings
}

export interface ClientDashboardData {
  welcome_name: string
  client_name: string
  kpis: {
    orders: number
    active_orders: number
    spent: number
    open_balance: number
    credit_limit: number | null
    credit_used: number
    credit_remaining: number | null
  }
  credit: ClientCredit
  recent_orders: ClientOrder[]
}

export interface ClientFaqItem {
  question: string
  answer: string
}

export const clientOrderStatusClasses: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-700",
  CONFIRMED: "bg-blue-100 text-blue-700",
  PRODUCTION: "bg-amber-100 text-amber-700",
  QC: "bg-orange-100 text-orange-700",
  READY: "bg-violet-100 text-violet-700",
  SHIPPED: "bg-cyan-100 text-cyan-700",
  DELIVERED: "bg-emerald-100 text-emerald-700",
  CANCELLED: "bg-rose-100 text-rose-700",
}

export const clientInvoiceStatusClasses: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-700",
  SENT: "bg-blue-100 text-blue-700",
  PARTIAL: "bg-amber-100 text-amber-700",
  PAID: "bg-emerald-100 text-emerald-700",
  OVERDUE: "bg-rose-100 text-rose-700",
  VOID: "bg-slate-200 text-slate-600",
}

type Paginated<T> = {
  items: T[]
  total: number
  page: number
  page_size?: number
  pages: number
}

const BASE = "/client"

export const clientService = {
  async login(payload: { email: string; password: string; tenant_id: string }): Promise<ClientSessionResponse> {
    const response = await apiClient.post<ClientSessionResponse>(`${BASE}/auth/login`, payload)
    return response.data
  },

  async logout(): Promise<{ status: string }> {
    const response = await apiClient.post(`${BASE}/auth/logout`)
    return response.data
  },

  async refresh(): Promise<{ access_token: string; token_type: string }> {
    const response = await apiClient.post(`${BASE}/auth/refresh`)
    return response.data
  },

  async forgotPassword(payload: { email: string; tenant_id: string }): Promise<{ message: string; reset_token?: string }> {
    const response = await apiClient.post(`${BASE}/auth/forgot-password`, payload)
    return response.data
  },

  async resetPassword(payload: { token: string; new_password: string }): Promise<{ message: string }> {
    const response = await apiClient.post(`${BASE}/auth/reset-password`, payload)
    return response.data
  },

  async getDashboard(): Promise<ClientDashboardData> {
    const response = await apiClient.get(`${BASE}/dashboard`)
    return response.data
  },

  async listOrders(params?: { page?: number; page_size?: number; status?: string; search?: string }): Promise<Paginated<ClientOrder>> {
    const response = await apiClient.get(`${BASE}/orders`, { params })
    return response.data
  },

  async getOrder(id: string): Promise<ClientOrder> {
    const response = await apiClient.get(`${BASE}/orders/${id}`)
    return response.data
  },

  async getOrderTracking(id: string): Promise<{ order_id: string; order_number: string; current_status: string; timeline: ClientTimelineStep[]; tracking: ClientOrder["tracking"] }> {
    const response = await apiClient.get(`${BASE}/orders/${id}/tracking`)
    return response.data
  },

  async reorder(payload: { order_id: string; lines?: Array<{ product_id: string; product_type: string; uom_id: string; quantity: number; unit_price?: number; tax_rate?: number }>; notes?: string }): Promise<ClientOrder> {
    const response = await apiClient.post(`${BASE}/orders/reorder`, payload)
    return response.data
  },

  async requestCancellation(id: string): Promise<{ status: string }> {
    const response = await apiClient.post(`${BASE}/orders/${id}/cancel-request`)
    return response.data
  },

  async listInvoices(params?: { page?: number; page_size?: number; status?: string }): Promise<Paginated<ClientInvoice>> {
    const response = await apiClient.get(`${BASE}/invoices`, { params })
    return response.data
  },

  async getInvoice(id: string): Promise<ClientInvoice> {
    const response = await apiClient.get(`${BASE}/invoices/${id}`)
    return response.data
  },

  async downloadInvoicePdf(id: string): Promise<string> {
    const response = await apiClient.get(`${BASE}/invoices/${id}/pdf`, { responseType: "blob" })
    return URL.createObjectURL(response.data)
  },

  async getCredit(): Promise<ClientCredit> {
    const response = await apiClient.get(`${BASE}/credit`)
    return response.data
  },

  async getProfile(): Promise<ClientProfile> {
    const response = await apiClient.get(`${BASE}/profile`)
    return response.data
  },

  async updateProfile(payload: { first_name?: string; last_name?: string; email?: string }) {
    const response = await apiClient.put(`${BASE}/profile`, payload)
    return response.data
  },

  async listAddresses(): Promise<ClientAddress[]> {
    const response = await apiClient.get(`${BASE}/addresses`)
    return response.data
  },

  async createAddress(payload: Omit<ClientAddress, "id" | "created_at" | "updated_at">): Promise<ClientAddress> {
    const response = await apiClient.post(`${BASE}/addresses`, payload)
    return response.data
  },

  async updateAddress(id: string, payload: Partial<Omit<ClientAddress, "id" | "created_at" | "updated_at">>): Promise<ClientAddress> {
    const response = await apiClient.put(`${BASE}/addresses/${id}`, payload)
    return response.data
  },

  async deleteAddress(id: string): Promise<{ status: string }> {
    const response = await apiClient.delete(`${BASE}/addresses/${id}`)
    return response.data
  },

  async listNotifications(params?: { unread_only?: boolean; page?: number; page_size?: number }): Promise<{ items: ClientNotification[]; total: number; unread_count: number; page: number; pages: number }> {
    const response = await apiClient.get(`${BASE}/notifications`, { params })
    return response.data
  },

  async markNotificationRead(id: string): Promise<{ marked_read: number }> {
    const response = await apiClient.put(`${BASE}/notifications/${id}/read`)
    return response.data
  },

  async getNotificationSettings(): Promise<ClientNotificationSettings> {
    const response = await apiClient.get(`${BASE}/notifications/settings`)
    return response.data
  },

  async updateNotificationSettings(payload: Partial<ClientNotificationSettings>): Promise<ClientNotificationSettings> {
    const response = await apiClient.put(`${BASE}/notifications/settings`, payload)
    return response.data
  },

  async getFaq(): Promise<ClientFaqItem[]> {
    const response = await apiClient.get(`${BASE}/support/faq`)
    return response.data
  },

  async submitSupportRequest(payload: { subject: string; message: string }): Promise<{ ticket_id: string; status: string }> {
    const response = await apiClient.post(`${BASE}/support/contact`, payload)
    return response.data
  },
}
