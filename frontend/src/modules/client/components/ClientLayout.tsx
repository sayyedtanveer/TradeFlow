import { type FormEvent, useMemo, useState } from "react"
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom"
import { Bell, CreditCard, Headset, LayoutDashboard, LogOut, Menu, Package2, ReceiptText, RefreshCcw, UserCircle2, X } from "lucide-react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useAuthStore } from "@/app/store/authStore"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"
import { clientService } from "../services/client.service"

const navItems = [
  { label: "Dashboard", to: "/client", icon: LayoutDashboard },
  { label: "My Orders", to: "/client/orders", icon: Package2 },
  { label: "Invoices", to: "/client/invoices", icon: ReceiptText },
  { label: "Reorder", to: "/client/reorder", icon: RefreshCcw },
  { label: "Credit Status", to: "/client/credit", icon: CreditCard },
  { label: "Profile", to: "/client/profile", icon: UserCircle2 },
  { label: "Support", to: "/client/support", icon: Headset },
]

const mobileNavItems = [navItems[0], navItems[1], navItems[2], navItems[5]]

export default function ClientLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [search, setSearch] = useState("")
  const { user, logout } = useAuthStore()

  const notificationsQuery = useQuery({
    queryKey: ["client-notifications"],
    queryFn: () => clientService.listNotifications({ page: 1, page_size: 8 }),
    refetchInterval: 30000,
  })

  const markNotificationRead = useMutation({
    mutationFn: (id: string) => clientService.markNotificationRead(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["client-notifications"] }),
  })

  const unreadCount = notificationsQuery.data?.unread_count ?? 0

  const topBarTitle = useMemo(() => {
    const active = navItems.find((item) => location.pathname === item.to || location.pathname.startsWith(`${item.to}/`))
    return active?.label ?? "Client Portal"
  }, [location.pathname])

  const handleLogout = async () => {
    try {
      await clientService.logout()
    } catch {
      // Client-side logout should still proceed even if the API session call fails.
    }
    logout()
    navigate("/client/login", { replace: true })
  }

  const handleSearchSubmit = (event: FormEvent) => {
    event.preventDefault()
    navigate(`/client/orders${search ? `?search=${encodeURIComponent(search)}` : ""}`)
  }

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#fffef9_0%,#f5f8ff_100%)] text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-[1600px]">
        <aside
          className={cn(
            "fixed inset-y-0 left-0 z-40 w-72 border-r border-slate-200 bg-white/90 p-6 shadow-xl backdrop-blur md:static md:translate-x-0",
            isSidebarOpen ? "translate-x-0" : "-translate-x-full",
            "transition-transform duration-300"
          )}
        >
          <div className="mb-8 flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.25em] text-slate-500">MedTrack</p>
              <h1 className="text-xl font-semibold">Client Portal</h1>
            </div>
            <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setIsSidebarOpen(false)}>
              <X className="h-4 w-4" />
            </Button>
          </div>

          <nav className="space-y-2">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/client"}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition-colors",
                    isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  )
                }
                onClick={() => setIsSidebarOpen(false)}
              >
                <item.icon className="h-4 w-4" />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="mt-10 rounded-3xl bg-slate-950 p-5 text-white">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-300">Signed In</p>
            <p className="mt-2 text-lg font-semibold">{user?.first_name} {user?.last_name}</p>
            <p className="text-sm text-slate-300">{user?.email}</p>
          </div>
        </aside>

        <div className="flex min-h-screen flex-1 flex-col">
          <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/85 px-4 py-4 backdrop-blur md:px-8">
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setIsSidebarOpen(true)}>
                <Menu className="h-5 w-5" />
              </Button>
              <div className="min-w-0 flex-1">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{topBarTitle}</p>
                <h2 className="truncate text-lg font-semibold">Self-service order and invoice tracking</h2>
              </div>

              <form onSubmit={handleSearchSubmit} className="hidden w-full max-w-sm md:block">
                <Input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search order number"
                  className="rounded-full border-slate-200 bg-slate-50"
                />
              </form>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="relative rounded-full border border-slate-200">
                    <Bell className="h-4 w-4" />
                    {unreadCount > 0 && (
                      <Badge className="absolute -right-1 -top-1 h-5 min-w-5 rounded-full px-1 text-[10px]">{unreadCount}</Badge>
                    )}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-80">
                  <DropdownMenuLabel>Notifications</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {notificationsQuery.data?.items?.length ? (
                    notificationsQuery.data.items.map((item) => (
                      <DropdownMenuItem key={item.id} className="block cursor-pointer py-3" onClick={() => !item.is_read && markNotificationRead.mutate(item.id)}>
                        <p className="font-medium">{item.title}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{item.message}</p>
                      </DropdownMenuItem>
                    ))
                  ) : (
                    <DropdownMenuItem disabled>No notifications yet</DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>

              <Button variant="outline" className="hidden rounded-full md:inline-flex" onClick={() => void handleLogout()}>
                <LogOut className="mr-2 h-4 w-4" />
                Log Out
              </Button>
            </div>
          </header>

          <main className="flex-1 px-4 py-6 pb-24 md:px-8 md:pb-8">
            <Outlet />
          </main>

          <nav className="fixed inset-x-0 bottom-0 z-30 border-t border-slate-200 bg-white/95 px-3 py-2 backdrop-blur md:hidden">
            <div className="grid grid-cols-4 gap-2">
              {mobileNavItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/client"}
                  className={({ isActive }) =>
                    cn(
                      "flex flex-col items-center gap-1 rounded-2xl px-2 py-2 text-[11px]",
                      isActive ? "bg-slate-900 text-white" : "text-slate-500"
                    )
                  }
                >
                  <item.icon className="h-4 w-4" />
                  <span>{item.label.replace("My ", "")}</span>
                </NavLink>
              ))}
            </div>
          </nav>
        </div>
      </div>
    </div>
  )
}
