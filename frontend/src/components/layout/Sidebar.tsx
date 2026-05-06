import { Link, useLocation } from "react-router-dom"
import { ChevronRight, PanelLeftClose, PanelLeftOpen } from "lucide-react"
import { useUIStore } from "@/app/store/uiStore"
import { useTenantStore } from "@/app/store/tenantStore"
import { usePermissions } from "@/hooks/usePermissions"
import { NAV_ITEMS, type NavItem } from "@/lib/constants"
import { normalizeRole } from "@/lib/roles.config"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

export function Sidebar() {
  const { isSidebarOpen, toggleSidebar, setSidebarOpen } = useUIStore()
  const { name: tenantName } = useTenantStore()
  const { role } = usePermissions()
  const location = useLocation()

  const normalizedRole = normalizeRole(role)
  const visibleNavItems = NAV_ITEMS.filter((item: NavItem) =>
    normalizedRole && item.roles.includes(normalizedRole)
  )

  const closeOnMobile = () => {
    if (typeof window !== "undefined" && window.innerWidth < 768) {
      setSidebarOpen(false)
    }
  }

  return (
    <>
      <button
        type="button"
        aria-label="Close navigation"
        onClick={() => setSidebarOpen(false)}
        className={cn(
          "fixed inset-0 z-30 bg-slate-950/45 backdrop-blur-sm transition-opacity md:hidden",
          isSidebarOpen ? "opacity-100" : "pointer-events-none opacity-0"
        )}
      />

      <aside
        className={cn(
          "erp-sidebar-shell fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-slate-800/80 text-slate-100 shadow-2xl transition-all duration-300 md:translate-x-0 md:shadow-none",
          isSidebarOpen ? "translate-x-0 md:w-72" : "-translate-x-full md:w-20"
        )}
      >
        <div className="flex h-20 items-center border-b border-slate-800 px-4">
          {isSidebarOpen ? (
            <div className="flex w-full items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-blue-300/80">
                  MedTrack ERP
                </p>
                <p className="truncate pt-1 text-lg font-semibold text-white">
                  {tenantName || "Factory Workspace"}
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleSidebar}
                className="shrink-0 rounded-xl text-slate-300 hover:bg-slate-800 hover:text-white"
              >
                <PanelLeftClose className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <div className="flex w-full justify-center">
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleSidebar}
                className="rounded-xl text-slate-300 hover:bg-slate-800 hover:text-white"
              >
                <PanelLeftOpen className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>

        <nav className="erp-dark-scrollbar flex-1 space-y-1.5 overflow-y-auto px-3 py-4 pr-2">
          {visibleNavItems.map((item) => {
            const isActive =
              location.pathname === item.href || location.pathname.startsWith(`${item.href}/`)

            return (
              <Link
                key={item.href}
                to={item.href}
                onClick={closeOnMobile}
                className={cn(
                  "group flex items-center rounded-2xl px-3 py-3 text-sm font-medium transition-all duration-200",
                  isActive
                    ? "bg-slate-800 text-white shadow-inner"
                    : "text-slate-400 hover:bg-slate-900 hover:text-white",
                  isSidebarOpen ? "gap-3" : "justify-center px-0"
                )}
                title={!isSidebarOpen ? item.title : undefined}
              >
                <item.icon
                  className={cn(
                    "h-5 w-5 shrink-0 transition-transform duration-200 group-hover:scale-105",
                    isActive ? "text-blue-400" : "text-slate-500 group-hover:text-slate-200"
                  )}
                />
                {isSidebarOpen && (
                  <>
                    <span className="truncate">{item.title}</span>
                    {isActive && <ChevronRight className="ml-auto h-4 w-4 text-slate-500" />}
                  </>
                )}
              </Link>
            )
          })}
        </nav>

        <div className={cn("border-t border-slate-800 px-4 py-4", !isSidebarOpen && "px-2")}>
          {isSidebarOpen ? (
            <div className="rounded-2xl border border-slate-800/80 bg-slate-900/70 px-4 py-3 backdrop-blur-sm">
              <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">Role</p>
              <div className="mt-2 flex items-center justify-between gap-3">
                <span className="truncate text-sm font-medium text-slate-200">{role}</span>
                <span className="rounded-full border border-slate-700 px-2 py-1 text-[11px] text-slate-400">
                  v0.1.0
                </span>
              </div>
            </div>
          ) : (
            <div className="flex justify-center">
              <span className="rounded-full border border-slate-800 px-2 py-1 text-[11px] text-slate-500">
                v0.1.0
              </span>
            </div>
          )}
        </div>
      </aside>
    </>
  )
}
