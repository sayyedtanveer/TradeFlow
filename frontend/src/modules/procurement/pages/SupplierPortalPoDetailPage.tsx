import { useCallback, useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { PackageCheck, SendToBack } from "lucide-react"
import { REALTIME_EVENT_NAME } from "@/components/notifications/RealtimeNotificationsBridge"
import ResponsiveDataList from "@/components/shared/ResponsiveDataList"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/hooks/use-toast"
import {
  SupplierPortalHeader,
  SupplierPortalStatusBadge,
  SupplierPortalTabs,
} from "@/modules/procurement/components/SupplierPortalChrome"
import { supplyChainApi, type PurchaseOrder } from "@/services/supply-chain.service"

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

  const loadPo = useCallback(
    async (silent = false) => {
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
    },
    [poId, toast]
  )

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

  if (!po) {
    return <p className="text-sm text-muted-foreground">Loading purchase order...</p>
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-8">
      <SupplierPortalHeader
        eyebrow="Supplier workspace"
        title={`Purchase order ${po.po_number}`}
        description="Review order value, line requirements, and dispatch the next shipment notice when goods are ready."
        backHref="/supplier-portal"
        backLabel="Portal"
        actions={
          normalizeStatus(po.status) === "sent" ? (
            <Button onClick={ack} className="w-full sm:w-auto">
              <PackageCheck className="h-4 w-4" />
              Acknowledge order
            </Button>
          ) : undefined
        }
      />

      <div className="erp-portal-section space-y-4">
        <SupplierPortalTabs />
      </div>

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(260px,0.34fr)]">
        <article className="erp-portal-section space-y-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="space-y-2">
              <p className="font-mono text-lg font-semibold text-slate-950">{po.po_number}</p>
              <SupplierPortalStatusBadge status={po.status} />
            </div>
            <div className="rounded-[24px] border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              Dispatch progress stays visible to the buyer after each shipment notice.
            </div>
          </div>
          <ResponsiveDataList
            data={po.lines}
            getRowKey={(line) => line.id}
            columns={[
              {
                key: "material",
                header: "Material",
                cell: (line) => <span className="font-mono text-xs text-slate-700">{line.material_id}</span>,
              },
              {
                key: "qty",
                header: "Qty",
                headerClassName: "text-right",
                className: "text-right",
                cell: (line) => line.quantity,
              },
              {
                key: "received",
                header: "Received",
                headerClassName: "text-right",
                className: "text-right",
                cell: (line) => line.received_quantity,
              },
              {
                key: "price",
                header: "Unit price",
                headerClassName: "text-right",
                className: "text-right",
                cell: (line) => formatCurrency(line.unit_price),
              },
            ]}
            renderMobileCard={(line) => (
              <article className="rounded-[22px] border border-slate-200 bg-white p-4 shadow-sm">
                <p className="font-mono text-xs text-slate-700">{line.material_id}</p>
                <div className="mt-3 grid grid-cols-3 gap-3 text-sm">
                  <div>
                    <p className="text-slate-500">Qty</p>
                    <p className="font-semibold text-slate-900">{line.quantity}</p>
                  </div>
                  <div>
                    <p className="text-slate-500">Received</p>
                    <p className="font-semibold text-slate-900">{line.received_quantity}</p>
                  </div>
                  <div>
                    <p className="text-slate-500">Unit price</p>
                    <p className="font-semibold text-slate-900">{formatCurrency(line.unit_price)}</p>
                  </div>
                </div>
              </article>
            )}
          />
        </article>

        <article className="erp-portal-section space-y-3">
          <p className="text-sm text-slate-500">Order value</p>
          <p className="text-3xl font-semibold tracking-tight text-slate-950">{formatCurrency(po.total_amount)}</p>
          <p className="text-sm text-slate-600">Use this as the commercial reference before raising shipment notices or invoices.</p>
        </article>
      </section>

      {["sent", "acknowledged", "partial"].includes(normalizeStatus(po.status)) && (
        <section className="erp-portal-section space-y-4">
          <div className="space-y-1">
            <h2 className="text-xl font-semibold text-slate-950">Create shipment notice</h2>
            <p className="text-sm text-slate-600">Tell the buyer what is leaving your warehouse so the receiving team can prepare the GRN flow.</p>
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
              <div key={line.id} className="grid gap-3 rounded-[22px] border border-slate-200 bg-slate-50 p-4 lg:grid-cols-[1fr_180px]">
                <div className="space-y-1">
                  <p className="font-mono text-xs text-slate-700">{line.material_id}</p>
                  <p className="text-sm text-slate-500">
                    Ordered {line.quantity}, received {line.received_quantity}
                  </p>
                </div>
                <Input
                  type="number"
                  min="0"
                  value={shipmentLines[line.id] ?? ""}
                  onChange={(event) => setShipmentLines((current) => ({ ...current, [line.id]: event.target.value }))}
                />
              </div>
            ))}
          </div>
          <div className="space-y-2">
            <Label>Remarks</Label>
            <Textarea value={remarks} onChange={(event) => setRemarks(event.target.value)} />
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button onClick={submitShipmentNotice} className="w-full sm:w-auto">
              <SendToBack className="h-4 w-4" />
              Submit shipment notice
            </Button>
            <Button variant="outline" asChild className="w-full sm:w-auto">
              <Link to="/supplier-portal/receipts">View receipt timeline</Link>
            </Button>
          </div>
        </section>
      )}

      {!["sent", "acknowledged", "partial"].includes(normalizeStatus(po.status)) && (
        <Alert>
          <AlertDescription>This purchase order is not currently open for new shipment notices.</AlertDescription>
        </Alert>
      )}
    </div>
  )
}
