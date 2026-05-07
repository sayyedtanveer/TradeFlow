import { apiClient } from "./api-client"
import type { SalesOrder } from "@/types/sales.types"

export type DeliveryLine = {
  id: string
  sales_order_line_id: string
  variant_id: string
  quantity: number
  created_at: string
}

export type Delivery = {
  id: string
  delivery_number: string
  sales_order_id: string
  status: "DRAFT" | "PACKING" | "SHIPPED" | "DELIVERED" | string
  carrier?: string | null
  tracking_number?: string | null
  shipped_at?: string | null
  delivered_at?: string | null
  notes?: string | null
  lines: DeliveryLine[]
  created_at: string
  updated_at: string
}

function normalizeDelivery(delivery: any): Delivery {
  return {
    ...delivery,
    status: String(delivery.status || "DRAFT").toUpperCase(),
    lines: Array.isArray(delivery.lines)
      ? delivery.lines.map((line: any) => ({ ...line, quantity: Number(line.quantity || 0) }))
      : [],
  }
}

export const deliveryService = {
  async list(params?: { sales_order_id?: string }): Promise<Delivery[]> {
    const { data } = await apiClient.get("/deliveries", { params })
    return (Array.isArray(data) ? data : []).map(normalizeDelivery)
  },

  async createFromOrder(order: SalesOrder, payload?: { carrier?: string; tracking_number?: string; notes?: string }) {
    const lines = order.lines
      .map((line) => ({
        sales_order_line_id: line.id,
        quantity: Math.max(Number(line.allocated_qty || 0) - Number(line.shipped_qty || 0), 0),
      }))
      .filter((line) => line.quantity > 0)

    const { data } = await apiClient.post("/deliveries", {
      sales_order_id: order.id,
      lines,
      carrier: payload?.carrier || null,
      tracking_number: payload?.tracking_number || null,
      notes: payload?.notes || null,
    })
    return normalizeDelivery(data)
  },

  async ship(deliveryId: string, payload?: { carrier?: string; tracking_number?: string }) {
    const { data } = await apiClient.post(`/deliveries/${deliveryId}/ship`, payload || {})
    return normalizeDelivery(data)
  },

  async deliver(deliveryId: string) {
    const { data } = await apiClient.post(`/deliveries/${deliveryId}/deliver`)
    return normalizeDelivery(data)
  },
}
