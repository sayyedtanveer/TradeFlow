import { Outlet } from "react-router-dom"
import { useUIStore } from "@/app/store/uiStore"
import { Sidebar } from "@/components/layout/Sidebar"
import { TopBar } from "@/components/layout/TopBar"
import { Breadcrumb } from "@/components/layout/Breadcrumb"
import { cn } from "@/lib/utils"

export default function DefaultLayout() {
  const { isSidebarOpen } = useUIStore()

  return (
    <div className="flex min-h-screen w-full flex-col bg-muted/40">
      <Sidebar />

      <div className={cn("flex flex-col sm:gap-4 sm:py-4 transition-all duration-300", isSidebarOpen ? "sm:pl-64" : "sm:pl-14")}>
        <TopBar />
        
        <main className="grid flex-1 items-start gap-4 p-4 sm:px-6 sm:py-0 md:gap-8">
          <Breadcrumb />
          <Outlet />
        </main>
      </div>
    </div>
  )
}

