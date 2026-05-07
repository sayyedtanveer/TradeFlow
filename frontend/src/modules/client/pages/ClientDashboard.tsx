import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { Activity, Banknote, CreditCard, Package2 } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import CreditProgress from "../components/CreditProgress"
import { clientOrderStatusClasses, clientService } from "../services/client.service"
import { formatCurrency, formatDate } from "../utils/formatters"

export default function ClientDashboard() {
  const dashboardQuery = useQuery({
    queryKey: ["client-dashboard"],
    queryFn: () => clientService.getDashboard(),
  })

  const dashboard = dashboardQuery.data

  return (
    <div className="space-y-6">
      <section className="erp-surface relative overflow-hidden px-5 py-6 sm:px-6 sm:py-8">
        <div className="absolute inset-y-0 right-0 hidden w-1/3 bg-gradient-to-l from-blue-50 via-sky-50/80 to-transparent lg:block" />
        <p className="text-xs uppercase tracking-[0.25em] text-blue-600">Welcome Back</p>
        <h1 className="mt-3 text-2xl font-semibold leading-tight text-slate-900 sm:text-3xl">
          {dashboard ? `${dashboard.welcome_name}, here is your latest account view.` : "Loading your portal..."}
        </h1>
        <p className="mt-3 max-w-2xl text-slate-500">
          Review recent orders, monitor open balances, and keep an eye on credit usage before sending another reorder request.
        </p>
      </section>

      {dashboardQuery.isLoading && (
        <section className="grid gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-32 rounded-[28px]" />
          ))}
        </section>
      )}

      {dashboardQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Unable to load dashboard</AlertTitle>
          <AlertDescription>Refresh the page or sign in again to reload your client snapshot.</AlertDescription>
        </Alert>
      )}

      {dashboard?.credit.is_low_credit && (
        <Alert>
          <AlertTitle>Low remaining credit</AlertTitle>
          <AlertDescription>
            You have {formatCurrency(dashboard.credit.credit_remaining)} left before your next order starts pushing against the credit ceiling.
          </AlertDescription>
        </Alert>
      )}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Orders", value: dashboard?.kpis.orders ?? 0, tone: "erp-kpi-gradient", helper: "portal total", icon: Package2 },
          { label: "Active Orders", value: dashboard?.kpis.active_orders ?? 0, tone: "erp-kpi-gradient-alt", helper: "in progress", icon: Activity },
          { label: "Spent", value: formatCurrency(dashboard?.kpis.spent ?? 0), tone: "erp-kpi-gradient-soft", helper: "lifetime billed", icon: Banknote },
          { label: "Open Balance", value: formatCurrency(dashboard?.kpis.open_balance ?? 0), tone: "erp-kpi-gradient", helper: "awaiting payment", icon: CreditCard },
        ].map((item) => (
          <Card key={item.label} className={`${item.tone} h-full overflow-hidden rounded-[28px]`}>
            <CardContent className="flex h-full min-h-[136px] flex-col justify-between p-5 pt-5 sm:min-h-[144px] sm:p-6 sm:pt-6">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-white drop-shadow-sm sm:tracking-[0.24em]">
                    {item.label}
                  </p>
                  <p className="mt-2 text-xs font-medium text-white/85 drop-shadow-sm">{item.helper}</p>
                </div>
                <div className="rounded-2xl border border-white/25 bg-white/20 p-2.5 shadow-sm backdrop-blur">
                  <item.icon className="h-4 w-4 text-white drop-shadow-sm" />
                </div>
              </div>
              <p className="mt-5 text-2xl font-bold leading-none text-white drop-shadow-sm sm:text-[2rem]">{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <Card className="rounded-[28px] border-slate-200/70">
          <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle>Recent Orders</CardTitle>
            <Button asChild variant="outline" className="w-full rounded-full sm:w-auto">
              <Link to="/client/orders">View All</Link>
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {dashboard?.recent_orders?.length ? (
              dashboard.recent_orders.map((order) => (
                <Link key={order.id} to={`/client/orders/${order.id}`} className="flex flex-col gap-3 rounded-2xl border border-slate-200 px-4 py-3 transition hover:border-slate-400 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-medium">{order.order_number}</p>
                    <p className="text-sm text-muted-foreground">Delivery {formatDate(order.delivery_date)}</p>
                  </div>
                  <div className="sm:text-right">
                    <Badge className={clientOrderStatusClasses[order.status] ?? "bg-slate-100 text-slate-700"}>{order.status}</Badge>
                    <p className="mt-2 text-sm font-medium">{formatCurrency(order.grand_total)}</p>
                  </div>
                </Link>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No orders yet.</p>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-[28px] border-slate-200/70">
          <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle>Credit Progress</CardTitle>
            <Button asChild variant="ghost" className="w-full rounded-full sm:w-auto">
              <Link to="/client/credit">Details</Link>
            </Button>
          </CardHeader>
          <CardContent className="space-y-6">
            <CreditProgress
              limit={dashboard?.credit.credit_limit ?? null}
              used={dashboard?.credit.credit_used ?? 0}
              remaining={dashboard?.credit.credit_remaining ?? null}
              usagePercent={dashboard?.credit.usage_percent ?? null}
            />
            <div className="grid gap-3 sm:grid-cols-3">
              <Button asChild className="w-full rounded-full">
                <Link to="/client/reorder">Start Reorder</Link>
              </Button>
              <Button asChild variant="outline" className="w-full rounded-full">
                <Link to="/client/invoices">Invoices</Link>
              </Button>
              <Button asChild variant="outline" className="w-full rounded-full">
                <Link to="/client/support">Support</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
