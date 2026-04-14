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
  Truck,
  ShieldAlert,
  LucideIcon,
} from "lucide-react"
import { UserRole, getRolesForModule } from "@/lib/roles.config"

export type NavItem = {
  title: string
  href: string
  icon: LucideIcon
  roles: UserRole[]
}

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
    roles: getRolesForModule("systemMap"),
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
    title: "Procurement",
    href: "/procurement",
    icon: Truck,
    roles: getRolesForModule("procurement"),
  },
  {
    title: "Capacity & MRP",
    href: "/mrp",
    icon: BarChart3,
    roles: [UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR],
  },
  {
    title: "Quality & QC",
    href: "/procurement/quality",
    icon: ShieldAlert,
    roles: getRolesForModule("quality"),
  },
  {
    title: "Sales",
    href: "/sales",
    icon: ShoppingCart,
    roles: getRolesForModule("sales"),
  },
  {
    title: "Shop floor",
    href: "/shop-floor",
    icon: Factory,
    roles: getRolesForModule("shopFloor"),
  },
  {
    title: "Reports",
    href: "/reports",
    icon: BarChart3,
    roles: getRolesForModule("reports"),
  },
  {
    title: "Supplier portal",
    href: "/supplier-portal",
    icon: Truck,
    roles: getRolesForModule("supplierPortal"),
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
