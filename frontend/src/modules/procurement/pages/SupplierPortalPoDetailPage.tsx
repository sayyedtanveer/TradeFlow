import { useCallback, useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { REALTIME_EVENT_NAME } from "@/components/notifications/RealtimeNotificationsBridge"
import { supplyChainApi, type PurchaseOrder } from "@/services/supply-chain.service"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/hooks/use-toast"

const normalizeStatus = (status: string) => status.trim().toLowerCase()
const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(value)

export default function SupplierPortalPoDetailPage() {
  const { poId } = useParams<{ poId: string }>()
  const { toast } = useToast()
  const [po, setPo] = useState<PurchaseOrder | null>(null)
  const [shipmentLines, setShipmentLines] = useState<Record<string, string>>({})
  const [vehicleNumber, setVehicleNumber] = useState("")
  const [trackingNumber, setTrackingNumber] = useState("")
  const [remarks, setRemarks] = useState("")

  const loadPo = useCallback(async (silent = false) => {
    if (!poId) return
    try {
      const r = await supplyChainApi.supplierPortalPO(poId)
      setPo(r.data)
      setShipmentLines((current) => {
        const next = { ...current }
        r.data.lines.forEach((line) => {
          if (next[line.id] == null) {
            next[line.id] = String(Math.max(line.quantity - line.received_quantity, 0))
          }
        })
        return next
      })
    } catch {
      if (!silent) toast({ title: "Could not load PO", variant: "destructive" })
    }
  }, [poId, toast])

  useEffect(() => {
    void loadPo()
  }, [loadPo])

  useEffect(() => {
    const handleRealtime = () => {
      void loadPo(true)
    }
    window.addEventListener(REALTIME_EVENT_NAME, handleRealtime)
    return () => window.removeEventListener(REALTIME_EVENT_NAME, handleRealtime)
  }, [loadPo])

  const ack = async () => {
    if (!poId) return
    try {
      await supplyChainApi.supplierAckPO(poId)
      await loadPo()
      toast({ title: "Acknowledged" })
    } catch {
      toast({ title: "Failed", variant: "destructive" })
    }
  }

  const submitShipmentNotice = async () => {
    if (!poId || !po) return
    const lines = po.lines
      .map((line) => ({
        po_line_id: line.id,
        quantity: Number(shipmentLines[line.id] ?? 0),
      }))
      .filter((line) => line.quantity > 0)

    if (!lines.length) {
      toast({ title: "Enter at least one shipment quantity", variant: "destructive" })
      return
    }

    try {
      await supplyChainApi.supplierCreateShipmentNotice(poId, {
        vehicle_number: vehicleNumber || undefined,
        tracking_number: trackingNumber || undefined,
        remarks: remarks || undefined,
        lines,
      })
      await loadPo()
      setVehicleNumber("")
      setTrackingNumber("")
      setRemarks("")
      toast({ title: "Shipment notice sent" })
    } catch (err: any) {
      toast({
        title: "Shipment notice failed",
        description: err?.response?.data?.detail || err?.message,
        variant: "destructive",
      })
    }
  }

  if (!po) return <p className="text-muted-foreground">Loading...</p>

  return (
    <div className="space-y-6 max-w-3xl">
      <Button variant="ghost" size="sm" asChild>
        <Link to="/supplier-portal">{"<- Portal"}</Link>
      </Button>
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border bg-card p-4 sm:col-span-2">
          <h1 className="text-2xl font-semibold font-mono">{po.po_number}</h1>
          <p className="text-sm text-muted-foreground">Status: {po.status}</p>
        </div>
        <div className="rounded-xl border bg-card p-4">
          <p className="text-sm text-muted-foreground">Order value</p>
          <p className="mt-2 text-xl font-semibold">{formatCurrency(po.total_amount)}</p>
        </div>
      </div>
      {normalizeStatus(po.status) === "sent" && (
        <Button onClick={ack}>Acknowledge order</Button>
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Line</TableHead>
            <TableHead className="text-right">Qty</TableHead>
            <TableHead className="text-right">Unit price</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {po.lines.map((line) => (
            <TableRow key={line.id}>
              <TableCell className="font-mono text-xs">{line.material_id}</TableCell>
              <TableCell className="text-right">{line.quantity}</TableCell>
              <TableCell className="text-right">{formatCurrency(line.unit_price)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {["sent", "acknowledged", "partial"].includes(normalizeStatus(po.status)) && (
        <section className="rounded-xl border bg-card p-4 space-y-4">
          <div>
            <h2 className="text-lg font-medium">Create shipment notice</h2>
            <p className="text-sm text-muted-foreground">
              Tell the buyer what is being dispatched. Receiving/GRN will update inventory later.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Vehicle number</Label>
              <Input value={vehicleNumber} onChange={(event) => setVehicleNumber(event.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Tracking number</Label>
              <Input value={trackingNumber} onChange={(event) => setTrackingNumber(event.target.value)} />
            </div>
          </div>
          <div className="space-y-3">
            {po.lines.map((line) => (
              <div key={line.id} className="grid gap-2 rounded-lg border p-3 sm:grid-cols-[1fr_160px]">
                <div>
                  <p className="font-mono text-xs">{line.material_id}</p>
                  <p className="text-xs text-muted-foreground">
                    Ordered {line.quantity}, received {line.received_quantity}
                  </p>
                </div>
                <Input
                  type="number"
                  min="0"
                  value={shipmentLines[line.id] ?? ""}
                  onChange={(event) =>
                    setShipmentLines((current) => ({ ...current, [line.id]: event.target.value }))
                  }
                />
              </div>
            ))}
          </div>
          <div className="space-y-2">
            <Label>Remarks</Label>
            <Textarea value={remarks} onChange={(event) => setRemarks(event.target.value)} />
          </div>
          <Button onClick={submitShipmentNotice}>Submit shipment notice</Button>
        </section>
      )}
    </div>
  )
}
