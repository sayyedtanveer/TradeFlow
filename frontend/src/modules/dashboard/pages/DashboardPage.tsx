import { useQuery } from "@tanstack/react-query"
import { reportsService } from "@/services/reports.service"
import { PageHeader } from "@/components/layout/PageHeader"
import { KPICard } from "../components/KPICard"
import { ActivityFeed } from "../components/ActivityFeed"
import { QuickActions } from "../components/QuickActions"
import { LowStockAlert } from "../components/LowStockAlert"
import { Skeleton } from "@/components/ui/skeleton"

export default function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard-data"],
    queryFn: reportsService.getDashboard,
  })

  // Basic derived state for low stock alerts from KPI data (mock logic)
  const lowStockKpi = data?.kpis.find((k) => k.label.includes("Low Stock"))
  const lowStockCount = lowStockKpi ? Number(lowStockKpi.value) : 0

  if (error) {
    return (
      <div className="flex h-[50vh] flex-col items-center justify-center p-8 text-center bg-destructive/10 rounded-lg">
        <h2 className="text-xl font-semibold text-destructive mb-2">Failed to load dashboard</h2>
        <p className="text-muted-foreground">Please check your connection and try again.</p>
      </div>
    )
  }

  return (
    <div className="grid w-full items-start gap-6">
      <PageHeader 
        title="Dashboard" 
        description="Overview of your manufacturing and inventory operations."
      />

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
        </div>
      ) : (
        <>
          <LowStockAlert count={lowStockCount} />

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {data?.kpis.map((kpi, index) => (
              <KPICard key={index} data={kpi} />
            ))}
          </div>

          <div className="grid gap-4 grid-cols-1 lg:grid-cols-3 mt-4">
            <ActivityFeed activities={data?.recentActivities || []} />
            <QuickActions />
          </div>
        </>
      )}
    </div>
  )
}
