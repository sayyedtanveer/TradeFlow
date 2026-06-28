// ─── Product Types ────────────────────────────────────────────────────────────

export interface ItemTemplate {
  id: string;
  tenant_id: string;
  code: string;
  item_code: string;
  item_type: "RAW" | "FG" | "SF" | string;
  name: string;
  description?: string;
  category_id?: string;
  base_unit_id?: string;
  attributes: { key: string; label: string; values?: string[] }[];
  code_locked: boolean;
  is_active: boolean;
}

export interface ItemVariant {
  id: string;
  tenant_id: string;
  template_id: string;
  code: string;
  name: string;
  variant_key: string;
  attribute_values: Record<string, string>;
  base_unit_id?: string;
  standard_cost: number;
  selling_price?: number;
  is_active: boolean;
}

export interface ItemTemplateListResponse {
  items: ItemTemplate[];
  total: number;
  page: number;
  page_size: number;
}

export interface ItemVariantListResponse {
  items: ItemVariant[];
  total: number;
  page: number;
  page_size: number;
}

/** Global variant search (subcontract FG picker) */
export interface ItemVariantSearchItem extends ItemVariant {
  base_unit_code?: string | null;
  stock_material_id?: string | null;
}

export interface ItemVariantSearchListResponse {
  items: ItemVariantSearchItem[];
  total: number;
  page: number;
  page_size: number;
}
