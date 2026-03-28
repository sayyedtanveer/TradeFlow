export interface Material {
  id: string;
  tenant_id: string;
  code: string;
  name: string;
  material_type: string;
  description: string | null;
  category_id: string | null;
  base_unit_id: string | null;
  current_stock: number;
  reserved_stock: number;
  available_stock: number;
  reorder_level: number | null;
  location_id: string | null;
  is_batch_tracked: boolean;
  is_serialized: boolean;
  is_active: boolean;
  is_low_stock: boolean;
}

export interface StockInfo {
  material_id: string;
  material_code: string;
  material_name: string;
  current_stock: number;
  reserved_stock: number;
  available_stock: number;
  base_unit_id: string | null;
  is_low_stock: boolean;
  reorder_level: number | null;
}

export type TransactionType = "in" | "out" | "transfer" | "adjustment";

export interface InventoryTransaction {
  id: string;
  material_id: string;
  transaction_type: TransactionType;
  quantity: number;
  unit_id: string | null;
  from_location_id: string | null;
  to_location_id: string | null;
  reference_type: string;
  reference_id: string | null;
  remarks: string | null;
  created_by: string;
  created_at: string;
}

// Master Data Types
export interface Category {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
}

export interface UnitOfMeasure {
  id: string;
  code: string;
  name: string;
  precision: number;
  is_active: boolean;
}

export interface Location {
  id: string;
  name: string;
  /** API may return `location_type` instead of `type` */
  type: string;
  location_type?: string;
  parent_id: string | null;
  parent_location_id?: string | null;
  is_active: boolean;
}

// Requests
export interface CreateMaterialInput {
  code: string;
  name: string;
  material_type: "raw" | "finished";
  description?: string | null;
  category_id?: string | null;
  base_unit_id?: string | null;
  reorder_level?: number | null;
  location_id?: string | null;
  is_batch_tracked?: boolean;
  is_serialized?: boolean;
}

export interface UpdateMaterialInput {
  name?: string;
  description?: string | null;
  category_id?: string | null;
  base_unit_id?: string | null;
  material_type?: "raw" | "finished";
  reorder_level?: number | null;
  location_id?: string | null;
  is_active?: boolean;
  is_batch_tracked?: boolean;
  is_serialized?: boolean;
}

export interface StockOperationInput {
  material_id: string;
  transaction_type: TransactionType;
  quantity: number;
  unit_id?: string | null;
  from_location_id?: string | null;
  to_location_id?: string | null;
  remarks?: string | null;
  reference_id?: string | null;
  new_quantity?: number; // Only used for ADJUSTMENT
}
