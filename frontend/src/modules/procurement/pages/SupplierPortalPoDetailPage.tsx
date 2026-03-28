import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { supplyChainApi, type PurchaseOrder } from "@/services/supply-chain.service"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useToast } from "@/hooks/use-toast"

export default function SupplierPortalPoDetailPage() {
  const { poId } = useParams<{ poId: string }>()
  const { toast } = useToast()
  const [po, setPo] = useState<PurchaseOrder | null>(null)

  useEffect(() => {
    if (!poId) return
    supplyChainApi
      .supplierPortalPO(poId)
      .then((r) => setPo(r.data))
      .catch(() => toast({ title: "Could not load PO", variant: "destructive" }))
  }, [poId, toast])

  const ack = async () => {
    if (!poId) return
    try {
      await supplyChainApi.supplierAckPO(poId)
      const r = await supplyChainApi.supplierPortalPO(poId)
      setPo(r.data)
      toast({ title: "Acknowledged" })
    } catch {
      toast({ title: "Failed", variant: "destructive" })
    }
  }

  if (!po) return <p className="text-muted-foreground">Loading…</p>

  return (
    <div className="space-y-6 max-w-3xl">
      <Button variant="ghost" size="sm" asChild>
        <Link to="/supplier-portal">← Portal</Link>
      </Button>
      <h1 className="text-2xl font-semibold font-mono">{po.po_number}</h1>
      <p className="text-sm text-muted-foreground">Status: {po.status}</p>
      {po.status === "sent" && (
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
          {po.lines.map((l) => (
            <TableRow key={l.id}>
              <TableCell className="font-mono text-xs">{l.material_id}</TableCell>
              <TableCell className="text-right">{l.quantity}</TableCell>
              <TableCell className="text-right">{l.unit_price}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
