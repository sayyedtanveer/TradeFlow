// Storekeeper Dashboard Page
import { useQuery } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { AlertCircle, Package, AlertTriangle } from "lucide-react"
import axios from "axios"

export default function StorekeeperDashboardPage() {
  const { data: issueQueue, isLoading: issueLoading } = useQuery({
    queryKey: ["storekeeper-issue-queue"],
    queryFn: async () => {
      const response = await axios.get("/api/v1/inventory/storekeeper/issue-queue")
      return response.data
    }
  })

  const { data: shortageQueue, isLoading: shortageLoading } = useQuery({
    queryKey: ["storekeeper-shortage-queue"],
    queryFn: async () => {
      const response = await axios.get("/api/v1/inventory/storekeeper/shortage-queue")
      return response.data
    }
  })

  const { data: partiallyIssued, isLoading: partialLoading } = useQuery({
    queryKey: ["storekeeper-partially-issued"],
    queryFn: async () => {
      const response = await axios.get("/api/v1/inventory/storekeeper/partially-issued")
      return response.data
    }
  })

  if (issueLoading || shortageLoading || partialLoading) {
    return <div className="p-8">Loading Storekeeper Dashboard...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Storekeeper Dashboard</h1>
          <p className="text-muted-foreground mt-2">
            Material issue queue, shortages, and partially issued work orders.
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border-l-4 border-l-blue-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              <Package className="w-4 h-4 mr-2 text-blue-500" />
              Pending Issues
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <span className="text-3xl font-bold">{issueQueue?.length || 0}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-orange-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              <AlertTriangle className="w-4 h-4 mr-2 text-orange-500" />
              Shortages
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <span className="text-3xl font-bold">{shortageQueue?.length || 0}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-amber-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              <AlertCircle className="w-4 h-4 mr-2 text-amber-500" />
              Partially Issued
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <span className="text-3xl font-bold">{partiallyIssued?.length || 0}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Issue Queue Table */}
      <Card>
        <CardHeader>
          <CardTitle>Pending Material Issues</CardTitle>
        </CardHeader>
        <CardContent>
          {issueQueue && issueQueue.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>WO Number</TableHead>
                  <TableHead>Material ID</TableHead>
                  <TableHead>Required</TableHead>
                  <TableHead>Issued</TableHead>
                  <TableHead>Remaining</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {issueQueue.map((issue: any) => (
                  <TableRow key={`${issue.work_order_id}-${issue.material_id}`}>
                    <TableCell className="font-mono">{issue.wo_number}</TableCell>
                    <TableCell className="font-mono text-xs">{issue.material_id}</TableCell>
                    <TableCell>{issue.required_quantity}</TableCell>
                    <TableCell>{issue.issued_quantity}</TableCell>
                    <TableCell className="font-semibold">{issue.remaining_quantity}</TableCell>
                    <TableCell>{issue.due_date || '-'}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{issue.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <Button size="sm" variant="outline">
                        Issue
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">No pending issues</p>
          )}
        </CardContent>
      </Card>

      {/* Shortage Queue Table */}
      <Card>
        <CardHeader>
          <CardTitle>Material Shortages</CardTitle>
        </CardHeader>
        <CardContent>
          {shortageQueue && shortageQueue.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>WO ID</TableHead>
                  <TableHead>Material ID</TableHead>
                  <TableHead>Required</TableHead>
                  <TableHead>Available</TableHead>
                  <TableHead>Shortage</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {shortageQueue.map((shortage: any) => (
                  <TableRow key={shortage.shortage_id}>
                    <TableCell className="font-mono text-xs">{shortage.work_order_id}</TableCell>
                    <TableCell className="font-mono text-xs">{shortage.material_id}</TableCell>
                    <TableCell>{shortage.required_quantity}</TableCell>
                    <TableCell>{shortage.available_quantity}</TableCell>
                    <TableCell className="text-red-600 font-semibold">{shortage.shortage_quantity}</TableCell>
                    <TableCell>
                      <Badge variant="destructive">{shortage.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">No shortages</p>
          )}
        </CardContent>
      </Card>

      {/* Partially Issued WOs Table */}
      <Card>
        <CardHeader>
          <CardTitle>Partially Issued Work Orders</CardTitle>
        </CardHeader>
        <CardContent>
          {partiallyIssued && partiallyIssued.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>WO Number</TableHead>
                  <TableHead>Product ID</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {partiallyIssued.map((wo: any) => (
                  <TableRow key={wo.work_order_id}>
                    <TableCell className="font-mono">{wo.wo_number}</TableCell>
                    <TableCell className="font-mono text-xs">{wo.product_id}</TableCell>
                    <TableCell>{wo.due_date || '-'}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">{wo.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">No partially issued WOs</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
