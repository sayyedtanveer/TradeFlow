import { apiClient } from "./api-client";
import { 
  Material, 
  StockInfo, 
  InventoryTransaction, 
  CreateMaterialInput, 
  UpdateMaterialInput, 
  StockOperationInput,
  Category,
  Location,
  UnitOfMeasure
} from "@/types/material.types";

export interface PaginatedMaterialsResponse {
  items: Material[];
  total: number;
  page: number;
  page_size: number;
}

export const materialService = {
  // ── Materials ───────────────────────────────────────────────────────────
  async getMaterials(params: {
    query?: string;
    category?: string;
    is_active?: boolean;
    page: number;
    page_size: number;
  }): Promise<PaginatedMaterialsResponse> {
    const { data } = await apiClient.get("/inventory/materials", { params });
    return data;
  },

  async getMaterial(id: string): Promise<Material> {
    const { data } = await apiClient.get(`/inventory/materials/${id}`);
    return data;
  },

  async createMaterial(payload: CreateMaterialInput): Promise<Material> {
    const { data } = await apiClient.post("/inventory/materials", payload);
    return data;
  },

  async updateMaterial(id: string, payload: UpdateMaterialInput): Promise<Material> {
    const { data } = await apiClient.put(`/inventory/materials/${id}`, payload);
    return data;
  },

  async deleteMaterial(id: string): Promise<void> {
    await apiClient.delete(`/inventory/materials/${id}`);
  },

  // ── Stock & Transactions ────────────────────────────────────────────────
  async getStockInfo(materialId: string): Promise<StockInfo> {
    const { data } = await apiClient.get(`/inventory/materials/${materialId}/stock`);
    return data;
  },

  async createTransaction(payload: StockOperationInput): Promise<Material> {
    const { data } = await apiClient.post("/inventory/transactions", payload);
    return data;
  },

  async getTransactions(params: {
    material_id?: string;
    page: number;
    page_size: number;
  }): Promise<InventoryTransaction[]> {
    const { data } = await apiClient.get("/inventory/transactions", { params });
    return data;
  },

  // ── Master Data ─────────────────────────────────────────────────────────
  async getCategories(): Promise<Category[]> {
    const { data } = await apiClient.get("/inventory/master-data/categories");
    return data;
  },

  async getLocations(params?: { type?: string }): Promise<Location[]> {
    const { data } = await apiClient.get("/inventory/master-data/locations", { params });
    return data;
  },

  async createLocation(body: {
    name: string;
    type: string;
    code?: string | null;
    parent_id?: string | null;
    is_active?: boolean;
  }): Promise<Location> {
    const { data } = await apiClient.post("/inventory/master-data/locations", body);
    return data;
  },

  async updateLocation(
    id: string,
    body: {
      name?: string;
      code?: string | null;
      parent_id?: string | null;
      is_active?: boolean;
    }
  ): Promise<Location> {
    const { data } = await apiClient.put(`/inventory/master-data/locations/${id}`, body);
    return data;
  },

  async getUnits(): Promise<UnitOfMeasure[]> {
    const { data } = await apiClient.get("/inventory/master-data/units");
    return data;
  },
};
