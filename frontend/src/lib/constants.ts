import {
  Package,
  ShoppingCart,
  LayoutDashboard,
  Users,
  Settings,
  ClipboardList,
  Factory,
  BarChart3,
  LucideIcon
} from "lucide-react"

export type NavItem = {
  title: string
  href: string
  icon: LucideIcon
  roles: string[] // Which roles can see this
}

export const NAV_ITEMS: NavItem[] = [
  {
    title: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
    roles: ["ADMIN", "MANAGER", "OPERATOR", "VIEWER"],
  },
  {
    title: "Inventory",
    href: "/inventory",
    icon: Package,
    roles: ["ADMIN", "MANAGER", "OPERATOR", "VIEWER"],
  },
  {
    title: "Work Orders",
    href: "/work-orders",
    icon: ClipboardList,
    roles: ["ADMIN", "MANAGER", "OPERATOR"],
  },
  {
    title: "Manufacturing",
    href: "/manufacturing",
    icon: Factory,
    roles: ["ADMIN", "MANAGER"],
  },
  {
    title: "Sales",
    href: "/sales",
    icon: ShoppingCart,
    roles: ["ADMIN", "MANAGER", "VIEWER"],
  },
  {
    title: "Reports",
    href: "/reports",
    icon: BarChart3,
    roles: ["ADMIN", "MANAGER"],
  },
  {
    title: "Users",
    href: "/users",
    icon: Users,
    roles: ["ADMIN"],
  },
  {
    title: "Settings",
    href: "/settings",
    icon: Settings,
    roles: ["ADMIN"],
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
  INVENTORY: "/inventory/materials",
  MATERIALS: "/inventory/materials",
  TRANSACTIONS: "/inventory/transactions",
  USERS: "/users",
}

