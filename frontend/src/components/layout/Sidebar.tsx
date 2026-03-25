import { Link, useLocation } from "react-router-dom"
import { useUIStore } from "@/app/store/uiStore"
import { useTenantStore } from "@/app/store/tenantStore"
import { usePermissions } from "@/hooks/usePermissions"
import { NAV_ITEMS, type NavItem } from "@/lib/constants"
import { normalizeRole } from "@/lib/roles.config"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { ChevronRight, PanelLeftClose, PanelLeftOpen } from "lucide-react"

export function Sidebar() {
  const { isSidebarOpen, toggleSidebar } = useUIStore()
  const { name: tenantName } = useTenantStore()
  const { role } = usePermissions()
  const location = useLocation()

  // Normalize role from backend (lowercase) to enum (uppercase) for comparison
  const normalizedRole = normalizeRole(role)

  // Filter items by current user role - now comparing enums, not strings
  const visibleNavItems = NAV_ITEMS.filter((item: NavItem) => 
    normalizedRole && item.roles.includes(normalizedRole)
  )

  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-20 flex flex-col border-r bg-background transition-all duration-300",
        isSidebarOpen ? "w-64" : "w-14"
      )}
    >
      {/* Expanded / Collapsed Content */}
      <div className="flex h-14 items-center border-b px-4">
        {isSidebarOpen ? (
          <div className="flex w-full items-center justify-between">
            <span className="font-semibold text-lg truncate pr-2">{tenantName || "MedTrack ERP"}</span>
            <Button variant="ghost" size="icon" onClick={toggleSidebar}>
              <PanelLeftClose className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <div className="flex w-full justify-center">
            <Button variant="ghost" size="icon" onClick={toggleSidebar}>
              <PanelLeftOpen className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>

      <nav className="flex-1 space-y-1 p-2 overflow-y-auto">
        {visibleNavItems.map((item) => {
          const isActive = location.pathname === item.href || location.pathname.startsWith(`${item.href}/`)
          return (
            <Link
              key={item.href}
              to={item.href}
              className={cn(
                "group flex items-center rounded-md px-3 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors",
                isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground",
                !isSidebarOpen && "justify-center px-0"
              )}
              title={!isSidebarOpen ? item.title : undefined}
            >
              <item.icon className={cn("h-5 w-5", isSidebarOpen && "mr-3", isActive && "text-primary")} />
              {isSidebarOpen && <span>{item.title}</span>}
              {isActive && isSidebarOpen && (
                <ChevronRight className="ml-auto h-4 w-4 opacity-50" />
              )}
            </Link>
          )
        })}
      </nav>

      {isSidebarOpen && (
        <div className="px-4 py-4 border-t text-xs text-muted-foreground flex justify-between">
          <span>v0.1.0</span>
          <span>{role}</span>
        </div>
      )}
    </aside>
  )
}
