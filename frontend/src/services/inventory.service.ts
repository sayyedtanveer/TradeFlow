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
  }
}

function toCreateMaterialPayload(payload: ProductPayload) {
  return {
    code: payload.sku,
    name: payload.name,
    description: payload.description ?? null,
    category_id: payload.category_id ?? payload.category ?? null,
    base_unit_id: payload.base_unit_id ?? null,
    location_id: payload.location_id ?? null,
    reorder_level: payload.reorder_point ?? 0,
    material_type: "finished",
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
    material_type: "finished",
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
