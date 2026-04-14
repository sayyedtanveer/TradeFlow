import { Link, useNavigate, useParams } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { toast } from "@/hooks/use-toast"
import OrderTimeline from "../components/OrderTimeline"
import { clientOrderStatusClasses, clientService } from "../services/client.service"
import { formatCurrency, formatDate, formatStatusLabel } from "../utils/formatters"

export default function OrderDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const orderQuery = useQuery({
    queryKey: ["client-order", id],
    queryFn: () => clientService.getOrder(id!),
    enabled: Boolean(id),
  })

  const trackingQuery = useQuery({
    queryKey: ["client-order-tracking", id],
    queryFn: () => clientService.getOrderTracking(id!),
    enabled: Boolean(id),
  })

  const cancelMutation = useMutation({
    mutationFn: () => clientService.requestCancellation(id!),
    onSuccess: () => {
      toast({
        title: "Cancellation request submitted",
        description: "Your order status will update after the MedTrack team reviews the request.",
      })
      void queryClient.invalidateQueries({ queryKey: ["client-order", id] })
      void queryClient.invalidateQueries({ queryKey: ["client-order-tracking", id] })
      void queryClient.invalidateQueries({ queryKey: ["client-orders"] })
      void queryClient.invalidateQueries({ queryKey: ["client-notifications"] })
    },
    onError: (error: Error) =>
      toast({
        title: "Cancellation request failed",
        description: error.message,
        variant: "destructive",
      }),
  })

  const order = orderQuery.data
  const tracking = trackingQuery.data
  const backorderLines = order?.lines.filter((line) => line.availability.backorder_warning) ?? []
  const canCancel = Boolean(order && !["DELIVERED", "CANCELLED"].includes(order.status))

  if (!id) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Order not found</AlertTitle>
        <AlertDescription>The requested order id is missing from the route.</AlertDescription>
      </Alert>
    )
  }

  if (orderQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-48 rounded-[32px]" />
        <Skeleton className="h-64 rounded-[32px]" />
        <Skeleton className="h-80 rounded-[32px]" />
      </div>
    )
  }

  if (orderQuery.isError || !order) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Unable to load order details</AlertTitle>
        <AlertDescription>This order may no longer be available in your client workspace.</AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[32px] bg-slate-950 px-6 py-8 text-white shadow-xl">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.25em] text-slate-300">Order Detail</p>
            <h1 className="mt-2 text-3xl font-semibold">{order.order_number}</h1>
            <p className="mt-3 max-w-2xl text-sm text-slate-300">
              Follow production progress, review availability warnings, and jump into a reorder when this order needs repeating.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button asChild variant="secondary" className="rounded-full">
              <Link to={`/client/reorder?orderId=${order.id}`}>Reorder</Link>
            </Button>
            {canCancel && (
              <Button
                variant="outline"
                className="rounded-full border-white/20 bg-transparent text-white hover:bg-white/10 hover:text-white"
                disabled={cancelMutation.isPending}
                onClick={() => cancelMutation.mutate()}
              >
                {cancelMutation.isPending ? "Requesting..." : "Request Cancellation"}
              </Button>
            )}
            <Button variant="outline" className="rounded-full border-white/20 bg-transparent text-white hover:bg-white/10 hover:text-white" onClick={() => navigate("/client/orders")}>
              Back to Orders
            </Button>
          </div>
        </div>
      </section>

      {backorderLines.length > 0 && (
        <Alert>
          <AlertTitle>Backorder warning</AlertTitle>
          <AlertDescription>
            {backorderLines.length} line item{backorderLines.length > 1 ? "s" : ""} may need additional planning before full shipment.
          </AlertDescription>
        </Alert>
      )}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Order Date", value: formatDate(order.order_date) },
          { label: "Delivery Date", value: formatDate(order.delivery_date) },
          { label: "Grand Total", value: formatCurrency(order.grand_total) },
          { label: "Payment Status", value: formatStatusLabel(order.payment_status) },
        ].map((item) => (
          <Card key={item.label} className="rounded-[28px] border-slate-200/70">
            <CardContent className="pt-6">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{item.label}</p>
              <p className="mt-3 text-2xl font-semibold">{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
        <Card className="rounded-[28px] border-slate-200/70">
          <CardHeader>
            <div className="flex flex-wrap items-center gap-3">
              <CardTitle>Status Timeline</CardTitle>
              <Badge className={clientOrderStatusClasses[order.status] ?? "bg-slate-100 text-slate-700"}>
                {formatStatusLabel(tracking?.current_status ?? order.status)}
              </Badge>
            </div>
            <CardDescription>Draft to delivery progress with color-coded stage tracking.</CardDescription>
          </CardHeader>
          <CardContent>
            <OrderTimeline steps={tracking?.timeline ?? order.timeline} />
          </CardContent>
        </Card>

        <Card className="rounded-[28px] border-slate-200/70">
          <CardHeader>
            <CardTitle>Tracking Summary</CardTitle>
            <CardDescription>Latest delivery and shipping references available to the client.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="rounded-3xl bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Shipping Status</p>
              <p className="mt-2 text-lg font-semibold">{formatStatusLabel(tracking?.tracking.shipping_status ?? order.tracking.shipping_status)}</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Estimated Delivery</p>
                <p className="mt-2 font-medium">{formatDate(tracking?.tracking.estimated_delivery_date ?? order.tracking.estimated_delivery_date)}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Tracking Reference</p>
                <p className="mt-2 font-medium">{tracking?.tracking.tracking_reference ?? order.tracking.tracking_reference ?? "Available after shipment"}</p>
              </div>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Order Notes</p>
              <p className="mt-2 leading-6 text-slate-600">{order.notes || "No notes were attached to this order."}</p>
            </div>
          </CardContent>
        </Card>
      </section>

      <Card className="rounded-[28px] border-slate-200/70">
        <CardHeader>
          <CardTitle>Line Items</CardTitle>
          <CardDescription>Availability checks help flag backorder risk before you repeat the order.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-hidden rounded-3xl border border-slate-200">
            <Table>
              <TableHeader className="bg-slate-50">
                <TableRow>
                  <TableHead>Product</TableHead>
                  <TableHead>Requested</TableHead>
                  <TableHead>Allocated</TableHead>
                  <TableHead>Shipped</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Availability</TableHead>
                  <TableHead className="text-right">Line Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {order.lines.map((line) => (
                  <TableRow key={line.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{line.product_name}</p>
                        <p className="text-xs text-muted-foreground">{line.product_code || line.product_type}</p>
                      </div>
                    </TableCell>
                    <TableCell>{line.quantity}</TableCell>
                    <TableCell>{line.allocated_quantity}</TableCell>
                    <TableCell>{line.shipped_quantity}</TableCell>
                    <TableCell>{formatStatusLabel(line.status)}</TableCell>
                    <TableCell>
                      <div className="max-w-xs">
                        <Badge className={line.availability.backorder_warning ? "bg-rose-100 text-rose-700" : "bg-emerald-100 text-emerald-700"}>
                          {line.availability.backorder_warning ? "Backorder Risk" : formatStatusLabel(line.availability.status)}
                        </Badge>
                        <p className="mt-2 text-xs leading-5 text-muted-foreground">{line.availability.message}</p>
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-medium">{formatCurrency(line.line_total)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
