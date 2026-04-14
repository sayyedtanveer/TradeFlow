import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
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
      <section className="rounded-[32px] bg-slate-950 px-6 py-8 text-white shadow-xl">
        <p className="text-xs uppercase tracking-[0.25em] text-slate-300">Welcome Back</p>
        <h1 className="mt-3 text-3xl font-semibold">
          {dashboard ? `${dashboard.welcome_name}, here is your latest account view.` : "Loading your portal..."}
        </h1>
        <p className="mt-3 max-w-2xl text-slate-300">
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

      <section className="grid gap-4 md:grid-cols-4">
        {[
          { label: "Orders", value: dashboard?.kpis.orders ?? 0 },
          { label: "Active Orders", value: dashboard?.kpis.active_orders ?? 0 },
          { label: "Spent", value: formatCurrency(dashboard?.kpis.spent ?? 0) },
          { label: "Open Balance", value: formatCurrency(dashboard?.kpis.open_balance ?? 0) },
        ].map((item) => (
          <Card key={item.label} className="rounded-[28px] border-slate-200/70">
            <CardContent className="pt-6">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{item.label}</p>
              <p className="mt-3 text-3xl font-semibold">{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <Card className="rounded-[28px] border-slate-200/70">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Orders</CardTitle>
            <Button asChild variant="outline" className="rounded-full">
              <Link to="/client/orders">View All</Link>
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {dashboard?.recent_orders?.length ? (
              dashboard.recent_orders.map((order) => (
                <Link key={order.id} to={`/client/orders/${order.id}`} className="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3 transition hover:border-slate-400">
                  <div>
                    <p className="font-medium">{order.order_number}</p>
                    <p className="text-sm text-muted-foreground">Delivery {formatDate(order.delivery_date)}</p>
                  </div>
                  <div className="text-right">
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
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Credit Progress</CardTitle>
            <Button asChild variant="ghost" className="rounded-full">
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
              <Button asChild className="rounded-full">
                <Link to="/client/reorder">Start Reorder</Link>
              </Button>
              <Button asChild variant="outline" className="rounded-full">
                <Link to="/client/invoices">Invoices</Link>
              </Button>
              <Button asChild variant="outline" className="rounded-full">
                <Link to="/client/support">Support</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
