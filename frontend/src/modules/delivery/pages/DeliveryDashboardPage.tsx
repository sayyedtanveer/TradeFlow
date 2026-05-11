// Delivery Dashboard Page
import { useQuery } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Truck, PackageCheck, Navigation, CheckCircle } from "lucide-react"
import axios from "axios"

export default function DeliveryDashboardPage() {
  const { data: dispatchQueue, isLoading: dispatchLoading } = useQuery({
    queryKey: ["delivery-dispatch-queue"],
    queryFn: async () => {
      const response = await axios.get("/api/v1/delivery/dispatch-queue")
      return response.data
    }
  })

  const { data: inTransitQueue, isLoading: inTransitLoading } = useQuery({
    queryKey: ["delivery-in-transit-queue"],
    queryFn: async () => {
      const response = await axios.get("/api/v1/delivery/in-transit-queue")
      return response.data
    }
  })

  const { data: deliveredQueue, isLoading: deliveredLoading } = useQuery({
    queryKey: ["delivery-delivered-queue"],
    queryFn: async () => {
      const response = await axios.get("/api/v1/delivery/delivered-queue")
      return response.data
    }
  })

  if (dispatchLoading || inTransitLoading || deliveredLoading) {
    return <div className="p-8">Loading Delivery Dashboard...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Delivery Dashboard</h1>
          <p className="text-muted-foreground mt-2">
            Dispatch queue, in-transit shipments, and delivery confirmations.
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border-l-4 border-l-blue-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              <PackageCheck className="w-4 h-4 mr-2 text-blue-500" />
              Ready to Ship
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <span className="text-3xl font-bold">{dispatchQueue?.length || 0}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-amber-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              <Navigation className="w-4 h-4 mr-2 text-amber-500" />
              In Transit
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <span className="text-3xl font-bold">{inTransitQueue?.length || 0}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-green-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
              Delivered
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <span className="text-3xl font-bold">{deliveredQueue?.length || 0}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Dispatch Queue Table */}
      <Card>
        <CardHeader>
          <CardTitle>Ready to Ship</CardTitle>
        </CardHeader>
        <CardContent>
          {dispatchQueue && dispatchQueue.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>DO Number</TableHead>
                  <TableHead>Customer ID</TableHead>
                  <TableHead>Shipping Date</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {dispatchQueue.map((deliveryOrder: any) => (
                  <TableRow key={deliveryOrder.delivery_order_id}>
                    <TableCell className="font-mono">{deliveryOrder.do_number}</TableCell>
                    <TableCell className="font-mono text-xs">{deliveryOrder.customer_id}</TableCell>
                    <TableCell>{deliveryOrder.shipping_date || '-'}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{deliveryOrder.priority}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{deliveryOrder.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <Button size="sm" variant="default">
                        <Truck className="w-3 h-3 mr-1" />
                        Dispatch
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">No orders ready to ship</p>
          )}
        </CardContent>
      </Card>

      {/* In Transit Queue Table */}
      <Card>
        <CardHeader>
          <CardTitle>In Transit</CardTitle>
        </CardHeader>
        <CardContent>
          {inTransitQueue && inTransitQueue.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>DO Number</TableHead>
                  <TableHead>Customer ID</TableHead>
                  <TableHead>Shipping Date</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {inTransitQueue.map((deliveryOrder: any) => (
                  <TableRow key={deliveryOrder.delivery_order_id}>
                    <TableCell className="font-mono">{deliveryOrder.do_number}</TableCell>
                    <TableCell className="font-mono text-xs">{deliveryOrder.customer_id}</TableCell>
                    <TableCell>{deliveryOrder.shipping_date || '-'}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{deliveryOrder.priority}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">{deliveryOrder.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <Button size="sm" variant="default">
                        <CheckCircle className="w-3 h-3 mr-1" />
                        Confirm Delivery
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">No in-transit shipments</p>
          )}
        </CardContent>
      </Card>

      {/* Delivered Queue Table */}
      <Card>
        <CardHeader>
          <CardTitle>Delivered Orders</CardTitle>
        </CardHeader>
        <CardContent>
          {deliveredQueue && deliveredQueue.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>DO Number</TableHead>
                  <TableHead>Customer ID</TableHead>
                  <TableHead>Shipping Date</TableHead>
                  <TableHead>Delivery Date</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {deliveredQueue.map((deliveryOrder: any) => (
                  <TableRow key={deliveryOrder.delivery_order_id}>
                    <TableCell className="font-mono">{deliveryOrder.do_number}</TableCell>
                    <TableCell className="font-mono text-xs">{deliveryOrder.customer_id}</TableCell>
                    <TableCell>{deliveryOrder.shipping_date || '-'}</TableCell>
                    <TableCell>{deliveryOrder.delivery_date || '-'}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{deliveryOrder.priority}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="default">{deliveryOrder.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">No delivered orders</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
