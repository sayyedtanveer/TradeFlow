// QC Dashboard Page
import { useQuery } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { CheckCircle, XCircle, RefreshCw, ClipboardCheck, AlertTriangle } from "lucide-react"
import axios from "axios"

export default function QCDashboardPage() {
  const { data: inspectionQueue, isLoading: inspectionLoading } = useQuery({
    queryKey: ["qc-inspection-queue"],
    queryFn: async () => {
      const response = await axios.get("/api/v1/work-orders/qc/inspection-queue")
      return response.data
    }
  })

  const { data: rejectedQueue, isLoading: rejectedLoading } = useQuery({
    queryKey: ["qc-rejected-queue"],
    queryFn: async () => {
      const response = await axios.get("/api/v1/work-orders/qc/rejected-queue")
      return response.data
    }
  })

  const { data: reworkQueue, isLoading: reworkLoading } = useQuery({
    queryKey: ["qc-rework-queue"],
    queryFn: async () => {
      const response = await axios.get("/api/v1/work-orders/qc/rework-queue")
      return response.data
    }
  })

  if (inspectionLoading || rejectedLoading || reworkLoading) {
    return <div className="p-8">Loading QC Dashboard...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">QC Dashboard</h1>
          <p className="text-muted-foreground mt-2">
            Inspection queue, rejected batches, and rework operations.
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border-l-4 border-l-cyan-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              <ClipboardCheck className="w-4 h-4 mr-2 text-cyan-500" />
              Pending Inspections
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <span className="text-3xl font-bold">{inspectionQueue?.length || 0}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-red-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              <XCircle className="w-4 h-4 mr-2 text-red-500" />
              Rejected Batches
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <span className="text-3xl font-bold">{rejectedQueue?.length || 0}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-orange-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              <RefreshCw className="w-4 h-4 mr-2 text-orange-500" />
              Rework Queue
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <span className="text-3xl font-bold">{reworkQueue?.length || 0}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Inspection Queue Table */}
      <Card>
        <CardHeader>
          <CardTitle>Pending Inspections</CardTitle>
        </CardHeader>
        <CardContent>
          {inspectionQueue && inspectionQueue.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>WO Number</TableHead>
                  <TableHead>Product ID</TableHead>
                  <TableHead>Produced Qty</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {inspectionQueue.map((wo: any) => (
                  <TableRow key={wo.work_order_id}>
                    <TableCell className="font-mono">{wo.wo_number}</TableCell>
                    <TableCell className="font-mono text-xs">{wo.product_id}</TableCell>
                    <TableCell>{wo.produced_quantity}</TableCell>
                    <TableCell>{wo.due_date || '-'}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{wo.priority}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{wo.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button size="sm" variant="default">
                          <CheckCircle className="w-3 h-3 mr-1" />
                          Approve
                        </Button>
                        <Button size="sm" variant="destructive">
                          <XCircle className="w-3 h-3 mr-1" />
                          Reject
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">No pending inspections</p>
          )}
        </CardContent>
      </Card>

      {/* Rejected Queue Table */}
      <Card>
        <CardHeader>
          <CardTitle>Rejected Batches</CardTitle>
        </CardHeader>
        <CardContent>
          {rejectedQueue && rejectedQueue.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>WO Number</TableHead>
                  <TableHead>Product ID</TableHead>
                  <TableHead>Produced Qty</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rejectedQueue.map((wo: any) => (
                  <TableRow key={wo.work_order_id}>
                    <TableCell className="font-mono">{wo.wo_number}</TableCell>
                    <TableCell className="font-mono text-xs">{wo.product_id}</TableCell>
                    <TableCell>{wo.produced_quantity}</TableCell>
                    <TableCell>{wo.due_date || '-'}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{wo.priority}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="destructive">{wo.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline">
                          <RefreshCw className="w-3 h-3 mr-1" />
                          Rework
                        </Button>
                        <Button size="sm" variant="destructive">
                          <AlertTriangle className="w-3 h-3 mr-1" />
                          Scrap
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">No rejected batches</p>
          )}
        </CardContent>
      </Card>

      {/* Rework Queue Table */}
      <Card>
        <CardHeader>
          <CardTitle>Rework Queue</CardTitle>
        </CardHeader>
        <CardContent>
          {reworkQueue && reworkQueue.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>WO Number</TableHead>
                  <TableHead>Product ID</TableHead>
                  <TableHead>Produced Qty</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reworkQueue.map((wo: any) => (
                  <TableRow key={wo.work_order_id}>
                    <TableCell className="font-mono">{wo.wo_number}</TableCell>
                    <TableCell className="font-mono text-xs">{wo.product_id}</TableCell>
                    <TableCell>{wo.produced_quantity}</TableCell>
                    <TableCell>{wo.due_date || '-'}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{wo.priority}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">{wo.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">No rework items</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
