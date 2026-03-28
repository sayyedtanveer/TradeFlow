/**
 * Shared TypeScript contract for supplier portal enhancement.
 */

export interface SupplierPurchaseOrderListItem {
  id: string;
  po_number: string;
  status: string;
  total_amount: number;
}

export interface SupplierPurchaseOrderLine {
  id: string;
  material_id: string;
  quantity: number;
  received_quantity: number;
  unit_price: number;
  line_total: number;
}

export interface SupplierPurchaseOrderDetail {
  id: string;
  po_number: string;
  supplier_id: string;
  status: string;
  order_date: string;
  expected_delivery: string | null;
  total_amount: number;
  notes: string | null;
  lines: SupplierPurchaseOrderLine[];
}

export interface SupplierQuotationCreateInput {
  material_id: string;
  quantity: number;
  unit_price: number;
  valid_until?: string | null;
  purchase_order_id?: string | null;
}

export interface SupplierQuotationUpdateInput {
  quantity?: number;
  unit_price?: number;
  valid_until?: string | null;
}

export interface SupplierQuotation {
  id: string;
  supplier_id: string;
  purchase_order_id: string | null;
  material_id: string;
  quantity: number;
  unit_price: number;
  valid_until: string | null;
  status: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface SupplierProfile {
  id: string;
  code: string;
  name: string;
  contact_person: string | null;
  email: string | null;
  phone: string | null;
  address?: string | null;
  gst?: string | null;
  payment_terms?: string | null;
  performance_rating?: number | null;
  is_active: boolean;
}

export interface SupplierProfileUpdateInput {
  contact_person?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  payment_terms?: string | null;
}

export interface SupplierInvoiceCreateInput {
  purchase_order_id?: string | null;
  invoice_number: string;
  invoice_date: string;
  due_date?: string | null;
  total_amount: number;
  notes?: string | null;
  attachment_url?: string | null;
}

export interface SupplierInvoiceListItem {
  id: string;
  invoice_number: string;
  purchase_order_id: string | null;
  invoice_date: string;
  due_date: string | null;
  status: string;
  total_amount: number;
  currency?: string | null;
  created_at?: string | null;
}

export interface SupplierInvoiceDetail extends SupplierInvoiceListItem {
  notes?: string | null;
  attachment_url?: string | null;
}

export interface SupplierPaymentListItem {
  id: string;
  invoice_id: string | null;
  payment_date: string;
  reference_number: string | null;
  amount: number;
  status?: string;
  notes?: string | null;
}