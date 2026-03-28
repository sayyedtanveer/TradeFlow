import { apiClient } from "./api-client"

const BASE = "/api/v1"

export type Supplier = {
  id: string
  code: string
  name: string
  contact_person?: string | null
  email?: string | null
  phone?: string | null
  is_active: boolean
}

export type PurchaseOrderLine = {
  id: string
  material_id: string
  quantity: number
  received_quantity: number
  unit_price: number
  line_total?: number
}

export type PurchaseOrder = {
  id: string
  po_number: string
  supplier_id: string
  status: string
  order_date: string
  expected_delivery?: string | null
  total_amount: number
  notes?: string | null
  lines: PurchaseOrderLine[]
}

export type SubcontractOrderSummary = {
  id: string
  order_number: string
  supplier_id: string
  product_id: string
  product_type: string
  quantity: number
  status: string
}

export type SubcontractOrderDetail = SubcontractOrderSummary & {
  issues: {
    id: string
    material_id: string
    quantity: number
    batch_number?: string | null
    issued_at?: string | null
  }[]
}

export type MaterialRequest = {
  id: string
  item_id: string
  item_type: string
  required_quantity: number
  fulfilled_quantity: number
  status: string
}

export type InspectionRow = {
  id: string
  reference_type: string
  reference_id: string
  result: string
  inspection_date: string
}

export type NCRRow = {
  id: string
  inspection_id: string | null
  ncr_type: string
  reason?: string | null
  action_taken?: string | null
  created_at?: string | null
}

export type QuarantineRow = {
  material_id: string
  material_code: string
  material_name: string
  location_id: string
  location_name: string
  quantity: number
}

export type InspectionTemplate = {
  id: string
  tenant_id: string
  name: string
  parameters: Record<string, unknown>[]
  is_active: boolean
}

export const supplyChainApi = {
  listSuppliers: () => apiClient.get<Supplier[]>(`${BASE}/suppliers`),
  createSupplier: (body: {
    code: string
    name: string
    contact_person?: string
    email?: string
    phone?: string
    address?: string
    gst?: string
    payment_terms?: string
  }) => apiClient.post<Supplier>(`${BASE}/suppliers`, body),
  updateSupplier: (
    id: string,
    body: {
      name?: string
      contact_person?: string
      email?: string
      phone?: string
      address?: string
      gst?: string
      payment_terms?: string
      performance_rating?: number
      is_active?: boolean
    }
  ) => apiClient.put<Supplier>(`${BASE}/suppliers/${id}`, body),

  listPurchaseOrders: () => apiClient.get<PurchaseOrder[]>(`${BASE}/purchase-orders`),
  getPurchaseOrder: (id: string) => apiClient.get<PurchaseOrder>(`${BASE}/purchase-orders/${id}`),
  createPurchaseOrder: (body: {
    supplier_id: string
    expected_delivery?: string
    notes?: string
    lines: { material_id: string; quantity: number; unit_price: number }[]
  }) => apiClient.post<{ id: string; po_number: string }>(`${BASE}/purchase-orders`, body),

  sendPO: (id: string) => apiClient.put(`${BASE}/purchase-orders/${id}/send`),
  acknowledgePO: (id: string) => apiClient.put(`${BASE}/purchase-orders/${id}/acknowledge`),
  receiveGoods: (
    id: string,
    body: { lines: { line_id: string; quantity: number }[]; warehouse_location_id?: string }
  ) => apiClient.put(`${BASE}/purchase-orders/${id}/receive`, body),

  qualityInspect: (body: Record<string, unknown>) => apiClient.post(`${BASE}/quality/inspect`, body),
  createNCR: (body: Record<string, unknown>) => apiClient.post(`${BASE}/quality/ncr`, body),
  listInspections: () => apiClient.get<InspectionRow[]>(`${BASE}/quality/inspections`),
  listNCRs: () => apiClient.get<NCRRow[]>(`${BASE}/quality/ncrs`),
  quarantineStock: () => apiClient.get<QuarantineRow[]>(`${BASE}/quarantine-stock`),

  listInspectionTemplates: () => apiClient.get<InspectionTemplate[]>(`${BASE}/inspection-templates`),
  getInspectionTemplate: (id: string) =>
    apiClient.get<InspectionTemplate>(`${BASE}/inspection-templates/${id}`),
  createInspectionTemplate: (body: {
    name: string
    parameters?: Record<string, unknown>[]
    is_active?: boolean
  }) => apiClient.post<InspectionTemplate>(`${BASE}/inspection-templates`, body),
  updateInspectionTemplate: (
    id: string,
    body: { name?: string; parameters?: Record<string, unknown>[]; is_active?: boolean }
  ) => apiClient.put<InspectionTemplate>(`${BASE}/inspection-templates/${id}`, body),
  deleteInspectionTemplate: (id: string) => apiClient.delete(`${BASE}/inspection-templates/${id}`),

  listMaterialRequests: () => apiClient.get<MaterialRequest[]>(`${BASE}/material-requests`),
  runMrp: () => apiClient.post<{ created: number }>(`${BASE}/material-requests/run-mrp`),

  listSubcontractOrders: () => apiClient.get<SubcontractOrderSummary[]>(`${BASE}/subcontract/orders`),
  getSubcontractOrder: (id: string) => apiClient.get<SubcontractOrderDetail>(`${BASE}/subcontract/orders/${id}`),
  createSubcontractOrder: (body: {
    supplier_id: string
    product_id: string
    product_type?: string
    quantity: number
  }) => apiClient.post(`${BASE}/subcontract/orders`, body),
  issueSubcontract: (orderId: string, body: Record<string, unknown>) =>
    apiClient.post(`${BASE}/subcontract/orders/${orderId}/issue`, body),
  receiveSubcontract: (orderId: string, body: Record<string, unknown>) =>
    apiClient.post(`${BASE}/subcontract/orders/${orderId}/receive`, body),

  supplierPortalPOs: () =>
    apiClient.get<{ id: string; po_number: string; status: string; total_amount: number }[]>(
      `${BASE}/supplier/purchase-orders`
    ),
  supplierPortalPO: (id: string) => apiClient.get<PurchaseOrder>(`${BASE}/supplier/purchase-orders/${id}`),
  supplierAckPO: (id: string) => apiClient.put(`${BASE}/supplier/purchase-orders/${id}/acknowledge`),
  supplierQuotation: (body: Record<string, unknown>) => apiClient.post(`${BASE}/supplier/quotations`, body),
}
