import {
  Package,
  ShoppingCart,
  LayoutDashboard,
  Users,
  Settings,
  ClipboardList,
  Factory,
  BarChart3,
  Layers,
  PackageSearch,
  Network,
  LucideIcon
} from "lucide-react"
import { UserRole, getRolesForModule } from "@/lib/roles.config"

export type NavItem = {
  title: string
  href: string
  icon: LucideIcon
  roles: UserRole[] // Use enum values instead of strings
}

// Use getRolesForModule() helper to get roles instead of hardcoding them
export const NAV_ITEMS: NavItem[] = [
  {
    title: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
    roles: getRolesForModule("dashboard"),
  },
  {
    title: "System Map",
    href: "/system-map",
    icon: Network,
    roles: getRolesForModule("dashboard"),
  },
  {
    title: "Products",
    href: "/products",
    icon: PackageSearch,
    roles: getRolesForModule("products"),
  },
  {
    title: "Bill of Materials",
    href: "/bom/list",
    icon: Layers,
    roles: getRolesForModule("bom"),
  },
  {
    title: "Manufacturing",
    href: "/manufacturing",
    icon: Factory,
    roles: getRolesForModule("manufacturing"),
  },
  {
    title: "Inventory",
    href: "/inventory",
    icon: Package,
    roles: getRolesForModule("inventory"),
  },
  {
    title: "Work Orders",
    href: "/work-orders",
    icon: ClipboardList,
    roles: getRolesForModule("workOrders"),
  },
  {
    title: "Sales",
    href: "/sales",
    icon: ShoppingCart,
    roles: getRolesForModule("sales"),
  },
  {
    title: "Reports",
    href: "/reports",
    icon: BarChart3,
    roles: getRolesForModule("reports"),
  },
  {
    title: "Users",
    href: "/users",
    icon: Users,
    roles: getRolesForModule("users"),
  },
  {
    title: "Settings",
    href: "/settings",
    icon: Settings,
    roles: getRolesForModule("settings"),
  },
]

export const ROLE_LABELS: Record<string, string> = {
  ADMIN: "Administrator",
  MANAGER: "Manager",
  OPERATOR: "Operator",
  VIEWER: "Viewer",
}

export const ROUTE_PATHS = {
  LOGIN: "/login",
  REGISTER: "/register",
  DASHBOARD: "/",
  PRODUCTS: "/products",
  BOM: "/bom/list",
  INVENTORY: "/inventory/materials",
  MATERIALS: "/inventory/materials",
  TRANSACTIONS: "/inventory/transactions",
  USERS: "/users",
}

