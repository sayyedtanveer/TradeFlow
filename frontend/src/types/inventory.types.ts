export interface KPIData {
  label: string
  value: number | string
  change: number
  trend: "up" | "down" | "neutral"
}

export interface DashboardReport {
  kpis: KPIData[]
  recentActivities: ActivityItem[]
}

export interface ActivityItem {
  id: string
  type: "movement" | "alert" | "system"
  description: string
  timestamp: string
  user?: string
}

export interface MetricChart {
  date: string
  count: number
}

// These types will be expanded when building the full Inventory module
export interface Product {
  id: string
  sku: string
  name: string
  description?: string
  category: string
  reorder_point: number
  price: number
  is_active: boolean
  stock_quantity?: number // From aggregate queries
  item_code?: string // Phase 2: Enterprise item code system
  code_locked?: boolean // Phase 2: Item code locked after creation
}
