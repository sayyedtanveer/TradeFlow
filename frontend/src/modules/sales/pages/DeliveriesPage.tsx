import { useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { PageHeader } from "@/components/layout/PageHeader"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { toast } from "@/hooks/use-toast"
import { deliveryService, type Delivery } from "@/services/delivery.service"
import { ordersApi } from "@/services/sales.service"
import { OrderStatus } from "@/types/sales.types"
import { PackageCheck, Truck } from "lucide-react"

const statusClass: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-700",
  PACKING: "bg-blue-100 text-blue-700",
  SHIPPED: "bg-amber-100 text-amber-800",
  DELIVERED: "bg-emerald-100 text-emerald-700",
}

export default function DeliveriesPage() {
  const queryClient = useQueryClient()
  const [selectedOrderId, setSelectedOrderId] = useState("")
  const [carrier, setCarrier] = useState("")
  const [trackingNumber, setTrackingNumber] = useState("")

  const { data: deliveries = [], isLoading } = useQuery({
    queryKey: ["deliveries"],
    queryFn: () => deliveryService.list(),
  })

  const { data: readyOrders } = useQuery({
    queryKey: ["sales-orders", "ready-for-delivery"],
    queryFn: () => ordersApi.list(50, 0, undefined, OrderStatus.READY),
  })

  const { data: selectedOrder } = useQuery({
    queryKey: ["sales-order", selectedOrderId],
    queryFn: () => ordersApi.get(selectedOrderId),
    enabled: Boolean(selectedOrderId),
  })

  const deliveryOrderLookup = useMemo(() => {
    const map = new Map<string, string>()
    readyOrders?.items.forEach((order) => map.set(order.id, order.order_number))
    return map
  }, [readyOrders])

  const createMutation = useMutation({
    mutationFn: async () => {
      if (!selectedOrder) throw new Error("Select an order before creating delivery.")
      return deliveryService.createFromOrder(selectedOrder, {
        carrier,
        tracking_number: trackingNumber,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["deliveries"] })
      queryClient.invalidateQueries({ queryKey: ["sales-orders"] })
      setSelectedOrderId("")
      setCarrier("")
      setTrackingNumber("")
      toast({ title: "Delivery created", description: "The delivery document is now ready for shipment." })
    },
    onError: (error: any) => {
      toast({
        title: "Delivery creation failed",
        description: error?.response?.data?.detail || error?.message || "Unable to create delivery.",
        variant: "destructive",
      })
    },
  })

  const shipMutation = useMutation({
    mutationFn: (delivery: Delivery) =>
      deliveryService.ship(delivery.id, {
        carrier: delivery.carrier || undefined,
        tracking_number: delivery.tracking_number || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["deliveries"] })
      queryClient.invalidateQueries({ queryKey: ["sales-orders"] })
    },
  })

  const deliverMutation = useMutation({
    mutationFn: (delivery: Delivery) => deliveryService.deliver(delivery.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["deliveries"] })
      queryClient.invalidateQueries({ queryKey: ["sales-orders"] })
      queryClient.invalidateQueries({ queryKey: ["finance-dashboard"] })
      toast({ title: "Delivery completed", description: "The linked sales order can now flow into invoicing." })
    },
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Deliveries"
        description="Create, ship, and complete outbound deliveries from confirmed sales allocations."
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <PackageCheck className="h-5 w-5 text-blue-600" />
            Create Delivery
          </CardTitle>
          <CardDescription>Only ready sales orders with allocated stock are shown.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-[1.5fr_1fr_1fr_auto] md:items-end">
          <div className="space-y-2">
            <Label>Sales Order</Label>
            <Select value={selectedOrderId} onValueChange={setSelectedOrderId}>
              <SelectTrigger>
                <SelectValue placeholder="Select ready order" />
              </SelectTrigger>
              <SelectContent>
                {readyOrders?.items.map((order) => (
                  <SelectItem key={order.id} value={order.id}>
                    {order.order_number} - {order.client_name || order.client_code || "Client"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Carrier</Label>
            <Input value={carrier} onChange={(event) => setCarrier(event.target.value)} placeholder="Carrier" />
          </div>
          <div className="space-y-2">
            <Label>Tracking</Label>
            <Input value={trackingNumber} onChange={(event) => setTrackingNumber(event.target.value)} placeholder="Tracking no." />
          </div>
          <Button disabled={!selectedOrder || createMutation.isPending} onClick={() => createMutation.mutate()}>
            {createMutation.isPending ? "Creating..." : "Create"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Truck className="h-5 w-5 text-blue-600" />
            Delivery Queue
          </CardTitle>
          <CardDescription>Completing a delivery triggers the existing sales-to-invoice backend flow.</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-slate-500">Loading deliveries...</p>
          ) : deliveries.length === 0 ? (
            <div className="rounded-lg border border-dashed p-6 text-center text-sm text-slate-500">
              No delivery documents found.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b bg-slate-50 text-left">
                  <tr>
                    <th className="px-4 py-3 font-medium text-slate-600">Delivery</th>
                    <th className="px-4 py-3 font-medium text-slate-600">Sales Order</th>
                    <th className="px-4 py-3 font-medium text-slate-600">Status</th>
                    <th className="px-4 py-3 font-medium text-slate-600">Tracking</th>
                    <th className="px-4 py-3 text-right font-medium text-slate-600">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {deliveries.map((delivery) => (
                    <tr key={delivery.id} className="border-b">
                      <td className="px-4 py-3 font-semibold text-slate-900">{delivery.delivery_number}</td>
                      <td className="px-4 py-3">{deliveryOrderLookup.get(delivery.sales_order_id) || "Linked order"}</td>
                      <td className="px-4 py-3">
                        <Badge className={statusClass[delivery.status] || "bg-slate-100 text-slate-700"}>
                          {delivery.status}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        {[delivery.carrier, delivery.tracking_number].filter(Boolean).join(" / ") || "-"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-2">
                          {["DRAFT", "PACKING"].includes(delivery.status) && (
                            <Button size="sm" variant="outline" onClick={() => shipMutation.mutate(delivery)}>
                              Ship
                            </Button>
                          )}
                          {delivery.status === "SHIPPED" && (
                            <Button size="sm" onClick={() => deliverMutation.mutate(delivery)}>
                              Complete
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
