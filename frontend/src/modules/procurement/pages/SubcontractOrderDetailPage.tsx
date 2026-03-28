import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { supplyChainApi, type SubcontractOrderDetail } from "@/services/supply-chain.service"
import { materialService } from "@/services/material.service"
import type { Location, Material } from "@/types/material.types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useToast } from "@/hooks/use-toast"
import { ProductVariantSelector } from "@/modules/procurement/components/ProductVariantSelector"

function locKind(l: Location & { location_type?: string }) {
  return l.location_type ?? (l as { type?: string }).type ?? ""
}

export default function SubcontractOrderDetailPage() {
  const { orderId } = useParams<{ orderId: string }>()
  const { toast } = useToast()
  const [order, setOrder] = useState<SubcontractOrderDetail | null>(null)
  const [materials, setMaterials] = useState<Material[]>([])
  const [locations, setLocations] = useState<(Location & { location_type?: string })[]>([])

  const [issueMat, setIssueMat] = useState("")
  const [issueQty, setIssueQty] = useState("1")
  const [issueFrom, setIssueFrom] = useState("")
  const [batch, setBatch] = useState("")

  const [recvMat, setRecvMat] = useState("")
  const [recvQty, setRecvQty] = useState("1")
  const [recvWh, setRecvWh] = useState("")

  const load = async () => {
    if (!orderId) return
    const { data } = await supplyChainApi.getSubcontractOrder(orderId)
    setOrder(data)
  }

  useEffect(() => {
    Promise.all([
      load(),
      materialService.getMaterials({ page: 1, page_size: 300 }),
      materialService.getLocations(),
    ])
      .then(([, mats, locs]) => {
        setMaterials(mats.items.filter((m) => m.material_type === "raw"))
        setLocations(locs as (Location & { location_type?: string })[])
        const wh = locs.find((l) => locKind(l as Location & { location_type?: string }) === "warehouse")
        if (wh) setRecvWh(wh.id)
        if (wh) setIssueFrom(wh.id)
      })
      .catch(() => toast({ title: "Failed to load", variant: "destructive" }))
  }, [orderId, toast])

  const issue = async () => {
    if (!orderId || !issueMat || !issueFrom) return
    try {
      await supplyChainApi.issueSubcontract(orderId, {
        material_id: issueMat,
        quantity: Number(issueQty),
        from_location_id: issueFrom,
        batch_number: batch || undefined,
      })
      toast({ title: "Material issued to subcontractor" })
      await load()
    } catch (e: unknown) {
      const d = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast({ title: d || "Issue failed", variant: "destructive" })
    }
  }

  const receive = async () => {
    if (!orderId || !recvMat || !recvWh) return
    try {
      await supplyChainApi.receiveSubcontract(orderId, {
        material_id: recvMat,
        quantity: Number(recvQty),
        warehouse_location_id: recvWh,
      })
      toast({ title: "Finished goods received" })
      await load()
    } catch (e: unknown) {
      const d = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast({ title: d || "Receive failed", variant: "destructive" })
    }
  }

  if (!order) return <p className="text-muted-foreground">Loading…</p>

  const warehouses = locations.filter((l) => locKind(l) === "warehouse" && l.is_active)

  return (
    <div className="space-y-8 max-w-3xl">
      <div>
        <Button variant="ghost" size="sm" asChild className="mb-2 -ml-2">
          <Link to="/procurement/subcontract">← Subcontract orders</Link>
        </Button>
        <h1 className="text-2xl font-semibold font-mono">{order.order_number}</h1>
        <p className="text-sm text-muted-foreground">
          Status: {order.status} · Product {order.product_id.slice(0, 8)}… · Qty {order.quantity}
        </p>
      </div>

      <section className="border rounded-lg p-4 space-y-3">
        <h2 className="font-medium">Issue raw material</h2>
        <p className="text-xs text-muted-foreground">Moves available stock from your warehouse to the subcontractor location.</p>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-2">
            <Label>Material</Label>
            <Select value={issueMat} onValueChange={setIssueMat}>
              <SelectTrigger>
                <SelectValue placeholder="RM" />
              </SelectTrigger>
              <SelectContent>
                {materials.map((m) => (
                  <SelectItem key={m.id} value={m.id}>
                    {m.code}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Quantity</Label>
            <Input type="number" value={issueQty} onChange={(e) => setIssueQty(e.target.value)} />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label>From location (warehouse)</Label>
            <Select value={issueFrom} onValueChange={setIssueFrom}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {warehouses.map((l) => (
                  <SelectItem key={l.id} value={l.id}>
                    {l.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label>Batch (optional)</Label>
            <Input value={batch} onChange={(e) => setBatch(e.target.value)} />
          </div>
        </div>
        <Button onClick={issue}>Issue to subcontractor</Button>
      </section>

      <section className="border rounded-lg p-4 space-y-3">
        <h2 className="font-medium">Receive finished goods</h2>
        <p className="text-xs text-muted-foreground">Adds FG material into warehouse available stock.</p>
        <div className="grid gap-3 sm:grid-cols-2">
          <ProductVariantSelector value={recvMat} onChange={setRecvMat} />
          <div className="space-y-2">
            <Label>Quantity</Label>
            <Input type="number" value={recvQty} onChange={(e) => setRecvQty(e.target.value)} />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label>Warehouse</Label>
            <Select value={recvWh} onValueChange={setRecvWh}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {warehouses.map((l) => (
                  <SelectItem key={l.id} value={l.id}>
                    {l.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <Button onClick={receive}>Receive FG</Button>
      </section>

      <section>
        <h2 className="font-medium mb-2">Issue history</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Material</TableHead>
              <TableHead className="text-right">Qty</TableHead>
              <TableHead>Batch</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {order.issues.map((i) => (
              <TableRow key={i.id}>
                <TableCell className="font-mono text-xs">{i.material_id}</TableCell>
                <TableCell className="text-right">{i.quantity}</TableCell>
                <TableCell>{i.batch_number || "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {order.issues.length === 0 && <p className="text-sm text-muted-foreground">No issues yet.</p>}
      </section>
    </div>
  )
}
