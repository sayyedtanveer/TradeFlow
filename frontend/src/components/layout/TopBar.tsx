import { useEffect, useState } from "react"
import { Menu, Bell, Moon, Sun, User as UserIcon, LogOut, Settings, Laptop, CloudOff, CloudSync } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { financeService } from "@/services/finance.service"
import { useAuth } from "@/hooks/useAuth"
import { useUIStore } from "@/app/store/uiStore"
import { formatDistanceToNow } from "date-fns"

export function TopBar() {
  const { user, logout } = useAuth()
  const { toggleSidebar, theme, setTheme, pendingSyncCount, clearSyncQueue } = useUIStore()
  const [isOffline, setIsOffline] = useState(!navigator.onLine)
  const qc = useQueryClient()

  // Fetch notifications
  const { data: notifData } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => financeService.getNotifications({ unread_only: false, page: 1, page_size: 10 }),
    refetchInterval: 30000, // Refresh every 30s
  })

  const markReadMutation = useMutation({
    mutationFn: (id: string) => financeService.markRead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  })

  const markAllReadMutation = useMutation({
    mutationFn: () => financeService.markAllRead(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  })

  useEffect(() => {
    const handleOnline = () => {
      setIsOffline(false)
      // Attempt to clear queue/sync on reconnect logic would go here
      // For now we just reset the badge
      if (pendingSyncCount > 0) {
        // mock sync success
        setTimeout(() => clearSyncQueue(), 1500)
      }
    }
    const handleOffline = () => setIsOffline(true)

    window.addEventListener("online", handleOnline)
    window.addEventListener("offline", handleOffline)

    return () => {
      window.removeEventListener("online", handleOnline)
      window.removeEventListener("offline", handleOffline)
    }
  }, [pendingSyncCount, clearSyncQueue])

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b bg-background px-4 shadow-sm sm:px-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={toggleSidebar}>
          <Menu className="h-5 w-5" />
          <span className="sr-only">Toggle sidebar</span>
        </Button>
      </div>

      <div className="flex items-center gap-4">
        {/* Network / Sync Status */}
        {isOffline ? (
          <Badge variant="destructive" className="hidden sm:flex items-center gap-1">
            <CloudOff className="h-3 w-3" />
            Offline Mode
          </Badge>
        ) : pendingSyncCount > 0 ? (
          <Badge variant="secondary" className="hidden sm:flex items-center gap-1 bg-amber-500/10 text-amber-600">
            <CloudSync className="h-3 w-3 animate-pulse" />
            Syncing ({pendingSyncCount})
          </Badge>
        ) : null}

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-5 w-5" />
              {notifData?.unread_count ? (
                <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-destructive animate-ping" />
              ) : null}
              {notifData?.unread_count ? (
                <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-destructive" />
              ) : null}
              <span className="sr-only">Notifications</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80 p-0 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b bg-slate-50 dark:bg-slate-900 border-slate-100 dark:border-slate-800">
              <p className="text-sm font-semibold">Notifications</p>
              {notifData?.unread_count ? (
                <button
                  onClick={() => markAllReadMutation.mutate()}
                  className="text-xs text-blue-600 hover:underline"
                >
                  Mark all read
                </button>
              ) : null}
            </div>
            <div className="max-h-[300px] overflow-y-auto">
              {!notifData?.items?.length ? (
                <div className="p-4 text-center text-sm text-slate-500">No recent notifications</div>
              ) : (
                <div className="divide-y divide-slate-100 dark:divide-slate-800">
                  {notifData.items.map((n) => (
                    <div
                      key={n.id}
                      className={`p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors ${!n.is_read ? 'bg-blue-50/50 dark:bg-blue-900/10' : ''}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="space-y-1">
                          <p className={`text-sm ${!n.is_read ? 'font-semibold text-slate-900 dark:text-white' : 'font-medium text-slate-700 dark:text-slate-300'}`}>
                            {n.title}
                          </p>
                          <p className="text-xs text-slate-500 line-clamp-2">{n.message}</p>
                          <p className="text-[10px] text-slate-400">
                            {formatDistanceToNow(new Date(n.sent_at), { addSuffix: true })}
                          </p>
                        </div>
                        {!n.is_read && (
                          <button
                            onClick={() => markReadMutation.mutate(n.id)}
                            className="h-2 w-2 rounded-full bg-blue-500 shrink-0 mt-1"
                            title="Mark as read"
                          />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="rounded-full bg-muted">
              <UserIcon className="h-5 w-5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">{user?.first_name} {user?.last_name}</p>
                <p className="text-xs leading-none text-muted-foreground">{user?.email}</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              <span>Settings</span>
            </DropdownMenuItem>
            
            <DropdownMenuSeparator />
            
            <DropdownMenuLabel className="text-xs text-muted-foreground">Theme</DropdownMenuLabel>
            <DropdownMenuItem onClick={() => setTheme("light")}>
              <Sun className="mr-2 h-4 w-4" />
              <span>Light</span>
              {theme === "light" && <span className="ml-auto text-xs">✓</span>}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme("dark")}>
              <Moon className="mr-2 h-4 w-4" />
              <span>Dark</span>
              {theme === "dark" && <span className="ml-auto text-xs">✓</span>}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme("system")}>
              <Laptop className="mr-2 h-4 w-4" />
              <span>System</span>
              {theme === "system" && <span className="ml-auto text-xs">✓</span>}
            </DropdownMenuItem>

            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={logout} className="text-destructive focus:bg-destructive focus:text-destructive-foreground">
              <LogOut className="mr-2 h-4 w-4" />
              <span>Log out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
