import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { supplyChainApi, type PurchaseOrder } from "@/services/supply-chain.service"
import { materialService } from "@/services/material.service"
import type { Material } from "@/types/material.types"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useToast } from "@/hooks/use-toast"

export default function PurchaseOrderDetailPage() {
  const { poId } = useParams<{ poId: string }>()
  const { toast } = useToast()
  const [po, setPo] = useState<PurchaseOrder | null>(null)
  const [matMap, setMatMap] = useState<Record<string, string>>({})

  const load = async () => {
    if (!poId) return
    const { data } = await supplyChainApi.getPurchaseOrder(poId)
    setPo(data)
    const mats = await materialService.getMaterials({ page: 1, page_size: 500 })
    const map: Record<string, string> = {}
    mats.items.forEach((m: Material) => {
      map[m.id] = `${m.code} (${m.name})`
    })
    setMatMap(map)
  }

  useEffect(() => {
    load().catch(() => toast({ title: "Failed to load PO", variant: "destructive" }))
  }, [poId, toast])

  const send = async () => {
    if (!poId) return
    try {
      await supplyChainApi.sendPO(poId)
      toast({ title: "PO sent to supplier" })
      await load()
    } catch {
      toast({ title: "Send failed", variant: "destructive" })
    }
  }

  const acknowledge = async () => {
    if (!poId) return
    try {
      await supplyChainApi.acknowledgePO(poId)
      toast({ title: "PO acknowledged" })
      await load()
    } catch {
      toast({ title: "Acknowledge failed", variant: "destructive" })
    }
  }

  if (!po) return <p className="text-muted-foreground">Loading…</p>

  const canSend = po.status === "draft"
  const canAck = ["sent", "partial"].includes(po.status)
  const canReceive = ["sent", "acknowledged", "partial"].includes(po.status)

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Button variant="ghost" size="sm" asChild className="mb-2 -ml-2">
            <Link to="/procurement/purchase-orders">← Back to list</Link>
          </Button>
          <h1 className="text-2xl font-semibold font-mono">{po.po_number}</h1>
          <p className="text-sm text-muted-foreground">
            Status: <strong>{po.status}</strong> · Ordered {po.order_date}
          </p>
          {po.notes && <p className="text-sm mt-1">{po.notes}</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          {canSend && (
            <Button onClick={send}>
              Send to supplier
            </Button>
          )}
          {canAck && (
            <Button variant="secondary" onClick={acknowledge}>
              Acknowledge (internal)
            </Button>
          )}
          {canReceive && (
            <Button variant="outline" asChild>
              <Link to={`/procurement/grn?poId=${po.id}`}>Goods receipt (GRN)</Link>
            </Button>
          )}
        </div>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Material</TableHead>
            <TableHead className="text-right">Ordered</TableHead>
            <TableHead className="text-right">Received</TableHead>
            <TableHead className="text-right">Unit price</TableHead>
            <TableHead className="text-right">Line total</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {po.lines.map((l) => (
            <TableRow key={l.id}>
              <TableCell>{matMap[l.material_id] || l.material_id}</TableCell>
              <TableCell className="text-right">{l.quantity}</TableCell>
              <TableCell className="text-right">{l.received_quantity}</TableCell>
              <TableCell className="text-right">{l.unit_price}</TableCell>
              <TableCell className="text-right">
                {(l.line_total ?? l.quantity * l.unit_price).toFixed(2)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
