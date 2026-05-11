import { Product } from "@/types/inventory.types"
import { Material } from "@/types/material.types"
import { apiClient } from "./api-client"

type ProductPayload = {
  sku: string
  name: string
  description?: string | null
  category?: string | null
  category_id?: string | null
  reorder_point?: number | null
  price?: number | null
  base_unit_id?: string | null
  location_id?: string | null

  // Item code system (Phase 2)
  item_code?: string | null
  item_type?: "raw" | "finished" | "semi_finished" | null
  code_locked?: boolean | null
}

function toProduct(material: Material): Product {
  return {
    id: material.id,
    sku: material.code,
    name: material.name,
    description: material.description ?? undefined,
    category: material.category_id ?? "Uncategorized",
    reorder_point: Number(material.reorder_level ?? 0),
    price: 0,
    is_active: material.is_active,
    stock_quantity: Number(material.current_stock ?? 0),
    item_code: (material as any).item_code ?? undefined,
    code_locked: (material as any).code_locked ?? false,
  }
}

function toCreateMaterialPayload(payload: ProductPayload) {
  return {
    // existing field (legacy SKU -> backend Material.code)
    code: payload.sku,

    name: payload.name,
    description: payload.description ?? null,

    category_id: payload.category_id ?? payload.category ?? null,
    base_unit_id: payload.base_unit_id ?? null,
    location_id: payload.location_id ?? null,
    reorder_level: payload.reorder_point ?? 0,

    // item code system
    item_code: payload.item_code ?? undefined,
    material_type: payload.item_type ?? "finished",
    code_locked: payload.code_locked ?? true,

    // defaults
    is_batch_tracked: false,
    is_serialized: false,
  }
}

function toUpdateMaterialPayload(payload: Partial<ProductPayload>) {
  return {
    name: payload.name,
    description: payload.description ?? undefined,
    category_id: payload.category_id ?? payload.category ?? undefined,
    base_unit_id: payload.base_unit_id ?? undefined,
    location_id: payload.location_id ?? undefined,
    reorder_level: payload.reorder_point,

    // item code system (backend will enforce locking rules)
    item_code: payload.item_code ?? undefined,
    material_type: payload.item_type ?? undefined,
    code_locked: payload.code_locked ?? undefined,
  }
}

export const inventoryService = {
  async getProducts(filters?: { search?: string; category?: string; lowStock?: boolean }): Promise<Product[]> {
    const { data } = await apiClient.get("/inventory/materials", {
      params: {
        query: filters?.search,
        category: filters?.category,
        material_type: "finished",
        page: 1,
        page_size: 500,
      },
    })
    const items = (data.items || []).map(toProduct)
    return filters?.lowStock ? items.filter((p: Product) => (p.stock_quantity ?? 0) <= p.reorder_point) : items
  },

  async getProduct(id: string): Promise<Product> {
    const { data } = await apiClient.get(`/inventory/materials/${id}`)
    return toProduct(data)
  },

  async createProduct(payload: ProductPayload): Promise<Product> {
    const { data } = await apiClient.post("/inventory/materials", toCreateMaterialPayload(payload))
    return toProduct(data)
  },

  async updateProduct(id: string, payload: Partial<ProductPayload>): Promise<Product> {
    const { data } = await apiClient.put(`/inventory/materials/${id}`, toUpdateMaterialPayload(payload))
    return toProduct(data)
  },

  async getProductByBarcode(sku: string): Promise<Product | null> {
    const products = await this.getProducts({ search: sku })
    return products.find((p) => p.sku === sku) || null
  },
}
