import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { REALTIME_EVENT_NAME } from "@/components/notifications/RealtimeNotificationsBridge"
import { supplyChainApi, type SupplierReceipt } from "@/services/supply-chain.service"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useToast } from "@/hooks/use-toast"

export default function SupplierPortalReceiptsPage() {
  const { toast } = useToast()
  const [rows, setRows] = useState<SupplierReceipt[]>([])
  const [error, setError] = useState<string | null>(null)

  const loadReceipts = async (silent = false) => {
    try {
      const response = await supplyChainApi.supplierListReceipts({ page_size: 100 })
      setRows(response.data.items)
      setError(null)
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || "Could not load receipts"
      setError(message)
      if (!silent) toast({ title: "Receipts unavailable", description: message, variant: "destructive" })
    }
  }

  useEffect(() => {
    void loadReceipts()
  }, [])

  useEffect(() => {
    const handleRealtime = () => void loadReceipts(true)
    window.addEventListener(REALTIME_EVENT_NAME, handleRealtime)
    return () => window.removeEventListener(REALTIME_EVENT_NAME, handleRealtime)
  }, [])

  return (
    <div className="max-w-5xl space-y-6">
      <Button variant="ghost" size="sm" asChild>
        <Link to="/supplier-portal">{"<- Portal"}</Link>
      </Button>
      <div>
        <h1 className="text-2xl font-semibold">Shipment notices and receipts</h1>
        <p className="text-sm text-muted-foreground">
          Track ASNs submitted by supplier users and GRNs completed by the receiving team.
        </p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {!error && rows.length === 0 ? (
        <Alert>
          <AlertDescription>No shipment notices or receipts yet. Open a PO to submit a shipment notice.</AlertDescription>
        </Alert>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Document</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Tracking</TableHead>
              <TableHead>Vehicle</TableHead>
              <TableHead className="text-right">Lines</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((receipt) => (
              <TableRow key={receipt.id}>
                <TableCell>
                  <div className="font-mono">{receipt.grn_number}</div>
                  <div className="text-xs text-muted-foreground">{receipt.created_at ?? "-"}</div>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary">{receipt.status}</Badge>
                </TableCell>
                <TableCell>{receipt.tracking_number ?? "-"}</TableCell>
                <TableCell>{receipt.vehicle_number ?? "-"}</TableCell>
                <TableCell className="text-right">{receipt.lines.length}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
