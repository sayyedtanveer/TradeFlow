import { useEffect, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { Plus, Search } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import ResponsiveDataList from "@/components/shared/ResponsiveDataList"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { clientOrderStatusClasses, clientService } from "../services/client.service"
import { formatCurrency, formatDate, formatStatusLabel } from "../utils/formatters"

const orderStatuses = ["ALL", "DRAFT", "PENDING_APPROVAL", "APPROVED", "REJECTED", "CONFIRMED", "PROCESSING", "PRODUCTION", "QC", "READY", "SHIPPED", "DELIVERED", "COMPLETED", "CANCELLED"]
const pageSize = 10

export default function OrdersList() {
  const [searchParams, setSearchParams] = useSearchParams()
  const currentPage = Math.max(1, Number(searchParams.get("page") ?? "1") || 1)
  const selectedStatus = searchParams.get("status") ?? "ALL"
  const searchValue = searchParams.get("search") ?? ""
  const [searchInput, setSearchInput] = useState(searchValue)

  useEffect(() => {
    setSearchInput(searchValue)
  }, [searchValue])

  const ordersQuery = useQuery({
    queryKey: ["client-orders", currentPage, selectedStatus, searchValue],
    queryFn: () =>
      clientService.listOrders({
        page: currentPage,
        page_size: pageSize,
        status: selectedStatus === "ALL" ? undefined : selectedStatus,
        search: searchValue || undefined,
      }),
  })

  const updateParams = (updates: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams)

    Object.entries(updates).forEach(([key, value]) => {
      if (value && value.trim().length > 0) {
        next.set(key, value)
      } else {
        next.delete(key)
      }
    })

    setSearchParams(next)
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[32px] border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.25em] text-slate-500">My Orders</p>
            <h1 className="mt-2 text-2xl font-semibold text-slate-900 sm:text-3xl">Track every order from draft to delivery.</h1>
            <p className="mt-3 max-w-2xl text-sm text-slate-600">
              Search by order number, filter by lifecycle stage, and jump straight into reorders when you need a fast repeat.
            </p>
          </div>
          <div className="erp-kpi-gradient w-full rounded-3xl px-5 py-4 text-white sm:max-w-xs">
            <p className="text-xs uppercase tracking-[0.2em] text-white/75">Order Snapshot</p>
            <p className="mt-2 text-2xl font-semibold">{ordersQuery.data?.total ?? 0}</p>
            <p className="text-sm text-white/75">orders visible in this portal</p>
          </div>
          <Button asChild className="w-full rounded-full sm:w-auto">
            <Link to="/client/orders/new">
              <Plus className="mr-2 h-4 w-4" />
              New Order
            </Link>
          </Button>
        </div>
      </section>

      <Card className="rounded-[28px] border-slate-200/70">
        <CardHeader className="gap-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <CardTitle>Order History</CardTitle>
              <CardDescription>Status colors match the client portal timeline and delivery stages.</CardDescription>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <form
                className="flex flex-col gap-2 sm:flex-row"
                onSubmit={(event) => {
                  event.preventDefault()
                  updateParams({ search: searchInput || null, page: "1" })
                }}
              >
                <Input
                  value={searchInput}
                  onChange={(event) => setSearchInput(event.target.value)}
                  placeholder="Search order number"
                  className="w-full min-w-0 sm:min-w-[220px]"
                />
                <Button type="submit" className="w-full rounded-full sm:w-auto">
                  <Search className="h-4 w-4" />
                  Search
                </Button>
              </form>

              <Select
                value={selectedStatus}
                onValueChange={(value) => updateParams({ status: value === "ALL" ? null : value, page: "1" })}
              >
                <SelectTrigger className="w-full sm:w-[200px]">
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  {orderStatuses.map((status) => (
                    <SelectItem key={status} value={status}>
                      {formatStatusLabel(status)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {ordersQuery.isLoading && (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <Skeleton key={index} className="h-16 rounded-2xl" />
              ))}
            </div>
          )}

          {ordersQuery.isError && (
            <Alert variant="destructive">
              <AlertTitle>Unable to load client orders</AlertTitle>
              <AlertDescription>Try refreshing this page or signing in again.</AlertDescription>
            </Alert>
          )}

          {!ordersQuery.isLoading && !ordersQuery.isError && (
            <>
              {ordersQuery.data?.items?.length ? (
                <ResponsiveDataList
                  data={ordersQuery.data.items}
                  getRowKey={(order) => order.id}
                  columns={[
                    {
                      key: "order",
                      header: "Order",
                      cell: (order) => (
                        <div>
                          <p className="font-medium text-slate-900">{order.order_number}</p>
                          <p className="text-xs text-muted-foreground">{order.line_count} line items</p>
                        </div>
                      ),
                    },
                    { key: "order_date", header: "Order Date", cell: (order) => formatDate(order.order_date) },
                    { key: "delivery_date", header: "Delivery", cell: (order) => formatDate(order.delivery_date) },
                    {
                      key: "status",
                      header: "Status",
                      cell: (order) => (
                        <Badge className={clientOrderStatusClasses[order.status] ?? "bg-slate-100 text-slate-700"}>
                          {formatStatusLabel(order.status)}
                        </Badge>
                      ),
                    },
                    { key: "payment", header: "Payment", cell: (order) => formatStatusLabel(order.payment_status) },
                    {
                      key: "total",
                      header: "Total",
                      headerClassName: "text-right",
                      className: "text-right font-medium",
                      cell: (order) => formatCurrency(order.grand_total),
                    },
                    {
                      key: "actions",
                      header: "Actions",
                      headerClassName: "text-right",
                      className: "text-right",
                      cell: (order) => (
                        <div className="flex flex-wrap justify-end gap-2">
                          <Button asChild variant="outline" className="rounded-full">
                            <Link to={`/client/orders/${order.id}`}>View</Link>
                          </Button>
                          <Button asChild className="rounded-full">
                            <Link to={`/client/reorder?orderId=${order.id}`}>Reorder</Link>
                          </Button>
                        </div>
                      ),
                    },
                  ]}
                  renderMobileCard={(order) => (
                    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition-all hover:shadow-md">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-base font-semibold text-slate-900">{order.order_number}</p>
                          <p className="mt-1 text-xs text-slate-500">{order.line_count} line items</p>
                        </div>
                        <Badge className={clientOrderStatusClasses[order.status] ?? "bg-slate-100 text-slate-700"}>
                          {formatStatusLabel(order.status)}
                        </Badge>
                      </div>
                      <div className="mt-4 space-y-2 text-sm">
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-slate-500">Order date</span>
                          <span>{formatDate(order.order_date)}</span>
                        </div>
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-slate-500">Delivery</span>
                          <span>{formatDate(order.delivery_date)}</span>
                        </div>
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-slate-500">Payment</span>
                          <span>{formatStatusLabel(order.payment_status)}</span>
                        </div>
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-slate-500">Total</span>
                          <span className="font-semibold">{formatCurrency(order.grand_total)}</span>
                        </div>
                      </div>
                      <div className="mt-4 flex flex-col gap-2">
                        <Button asChild variant="outline" className="w-full rounded-full">
                          <Link to={`/client/orders/${order.id}`}>View</Link>
                        </Button>
                        <Button asChild className="w-full rounded-full">
                          <Link to={`/client/reorder?orderId=${order.id}`}>Reorder</Link>
                        </Button>
                      </div>
                    </div>
                  )}
                />
              ) : (
                <div className="rounded-3xl border border-dashed border-slate-300 px-4 py-10 text-center text-sm text-muted-foreground">
                  No orders matched your current filters.
                </div>
              )}

              <div className="flex flex-col gap-3 rounded-3xl border border-slate-200 bg-slate-50 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-slate-600">
                  Page {ordersQuery.data?.page ?? currentPage} of {Math.max(ordersQuery.data?.pages ?? 1, 1)}
                </p>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Button
                    variant="outline"
                    className="w-full rounded-full sm:w-auto"
                    disabled={currentPage <= 1}
                    onClick={() => updateParams({ page: String(currentPage - 1) })}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full rounded-full sm:w-auto"
                    disabled={!ordersQuery.data || currentPage >= Math.max(ordersQuery.data.pages, 1)}
                    onClick={() => updateParams({ page: String(currentPage + 1) })}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
