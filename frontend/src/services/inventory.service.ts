import { Product } from "@/types/inventory.types"

// Temporary mock backend behavior for Phase 1 frontend implementation
export const mockProducts: Product[] = [
  { id: "1", sku: "SKU-001", name: "Raw Material A", category: "Raw Materials", reorder_point: 100, price: 10.50, is_active: true, stock_quantity: 450 },
  { id: "2", sku: "SKU-002", name: "Packaging Box Large", category: "Packaging", reorder_point: 500, price: 1.20, is_active: true, stock_quantity: 1200 },
  { id: "3", sku: "SKU-003", name: "Active Ingredient X", category: "Raw Materials", reorder_point: 50, price: 150.00, is_active: true, stock_quantity: 42 },
]

export const inventoryService = {
  async getProducts(filters?: { search?: string; category?: string; lowStock?: boolean }): Promise<Product[]> {
    try {
      // In production:
      // const response = await apiClient.get<Product[]>("/inventory/products", { params: filters })
      // return response.data
      
      await new Promise(resolve => setTimeout(resolve, 500))
      let result = [...mockProducts]

      if (filters?.search) {
        const search = filters.search.toLowerCase()
        result = result.filter(p => p.name.toLowerCase().includes(search) || p.sku.toLowerCase().includes(search))
      }
      
      if (filters?.category) {
        result = result.filter(p => p.category === filters.category)
      }

      if (filters?.lowStock) {
        result = result.filter(p => p.stock_quantity! <= p.reorder_point)
      }

      return result
    } catch (e) {
      throw e
    }
  },

  async getProduct(id: string): Promise<Product> {
    await new Promise(resolve => setTimeout(resolve, 300))
    const product = mockProducts.find(p => p.id === id)
    if (!product) throw new Error("Product not found")
    return product
  },

  async getProductByBarcode(sku: string): Promise<Product | null> {
    await new Promise(resolve => setTimeout(resolve, 300))
    return mockProducts.find(p => p.sku === sku) || null
  }
}
