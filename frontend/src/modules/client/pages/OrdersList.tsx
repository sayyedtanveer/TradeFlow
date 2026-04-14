import { useEffect, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { Search } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { clientOrderStatusClasses, clientService } from "../services/client.service"
import { formatCurrency, formatDate, formatStatusLabel } from "../utils/formatters"

const orderStatuses = ["ALL", "DRAFT", "CONFIRMED", "PRODUCTION", "QC", "READY", "SHIPPED", "DELIVERED", "CANCELLED"]
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
      <section className="rounded-[32px] border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.25em] text-slate-500">My Orders</p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-900">Track every order from draft to delivery.</h1>
            <p className="mt-3 max-w-2xl text-sm text-slate-600">
              Search by order number, filter by lifecycle stage, and jump straight into reorders when you need a fast repeat.
            </p>
          </div>
          <div className="rounded-3xl bg-slate-950 px-5 py-4 text-white">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-300">Order Snapshot</p>
            <p className="mt-2 text-2xl font-semibold">{ordersQuery.data?.total ?? 0}</p>
            <p className="text-sm text-slate-300">orders visible in this portal</p>
          </div>
        </div>
      </section>

      <Card className="rounded-[28px] border-slate-200/70">
        <CardHeader className="gap-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <CardTitle>Order History</CardTitle>
              <CardDescription>Status colors match the client portal timeline and delivery stages.</CardDescription>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row">
              <form
                className="flex gap-2"
                onSubmit={(event) => {
                  event.preventDefault()
                  updateParams({ search: searchInput || null, page: "1" })
                }}
              >
                <Input
                  value={searchInput}
                  onChange={(event) => setSearchInput(event.target.value)}
                  placeholder="Search order number"
                  className="min-w-[220px]"
                />
                <Button type="submit" className="rounded-full">
                  <Search className="h-4 w-4" />
                  Search
                </Button>
              </form>

              <Select
                value={selectedStatus}
                onValueChange={(value) => updateParams({ status: value === "ALL" ? null : value, page: "1" })}
              >
                <SelectTrigger className="w-[200px]">
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
              <div className="overflow-hidden rounded-3xl border border-slate-200">
                <Table>
                  <TableHeader className="bg-slate-50">
                    <TableRow>
                      <TableHead>Order</TableHead>
                      <TableHead>Order Date</TableHead>
                      <TableHead>Delivery</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Payment</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {ordersQuery.data?.items?.length ? (
                      ordersQuery.data.items.map((order) => (
                        <TableRow key={order.id}>
                          <TableCell>
                            <div>
                              <p className="font-medium text-slate-900">{order.order_number}</p>
                              <p className="text-xs text-muted-foreground">{order.line_count} line items</p>
                            </div>
                          </TableCell>
                          <TableCell>{formatDate(order.order_date)}</TableCell>
                          <TableCell>{formatDate(order.delivery_date)}</TableCell>
                          <TableCell>
                            <Badge className={clientOrderStatusClasses[order.status] ?? "bg-slate-100 text-slate-700"}>
                              {formatStatusLabel(order.status)}
                            </Badge>
                          </TableCell>
                          <TableCell>{formatStatusLabel(order.payment_status)}</TableCell>
                          <TableCell className="text-right font-medium">{formatCurrency(order.grand_total)}</TableCell>
                          <TableCell>
                            <div className="flex justify-end gap-2">
                              <Button asChild variant="outline" className="rounded-full">
                                <Link to={`/client/orders/${order.id}`}>View</Link>
                              </Button>
                              <Button asChild className="rounded-full">
                                <Link to={`/client/reorder?orderId=${order.id}`}>Reorder</Link>
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={7} className="py-10 text-center text-sm text-muted-foreground">
                          No orders matched your current filters.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>

              <div className="flex flex-col gap-3 rounded-3xl border border-slate-200 bg-slate-50 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-slate-600">
                  Page {ordersQuery.data?.page ?? currentPage} of {Math.max(ordersQuery.data?.pages ?? 1, 1)}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    className="rounded-full"
                    disabled={currentPage <= 1}
                    onClick={() => updateParams({ page: String(currentPage - 1) })}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    className="rounded-full"
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
