import { useEffect, useMemo, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { supplyChainApi, type PurchaseOrder } from "@/services/supply-chain.service"
import { materialService } from "@/services/material.service"
import type { Location } from "@/types/material.types"
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

function locKind(l: Location & { location_type?: string }) {
  return l.location_type ?? (l as { type?: string }).type ?? ""
}

export default function GrnPage() {
  const { toast } = useToast()
  const [searchParams] = useSearchParams()

  const [poList, setPoList] = useState<PurchaseOrder[]>([])
  const [poId, setPoId] = useState("")
  const [po, setPo] = useState<PurchaseOrder | null>(null)
  const [locations, setLocations] = useState<(Location & { location_type?: string })[]>([])
  const [warehouseId, setWarehouseId] = useState("")
  const [qtyByLine, setQtyByLine] = useState<Record<string, string>>({})

  useEffect(() => {
    materialService.getLocations().then((locs) => {
      const typed = locs as (Location & { location_type?: string })[]
      setLocations(typed)
      const wh = typed.find((l) => locKind(l) === "warehouse")
      if (wh) setWarehouseId(wh.id)
    })
  }, [])

  useEffect(() => {
    supplyChainApi
      .listPurchaseOrders()
      .then((r) => {
        setPoList(r.data)
        const receivable = r.data.filter((p) => ["sent", "acknowledged", "partial"].includes(p.status))
        const fromUrl = searchParams.get("poId")
        setPoId((prev) => {
          if (fromUrl) return fromUrl
          if (prev) return prev
          return receivable[0]?.id ?? ""
        })
      })
      .catch(() => {})
  }, [searchParams])

  useEffect(() => {
    if (!poId) {
      setPo(null)
      return
    }
    supplyChainApi
      .getPurchaseOrder(poId)
      .then((r) => {
        setPo(r.data)
        const q: Record<string, string> = {}
        r.data.lines.forEach((l) => {
          const max = l.quantity - l.received_quantity
          q[l.id] = max > 0 ? String(max) : "0"
        })
        setQtyByLine(q)
      })
      .catch(() => toast({ title: "Could not load PO", variant: "destructive" }))
  }, [poId, toast])

  const warehouseLocations = useMemo(
    () => locations.filter((l) => locKind(l) === "warehouse" && l.is_active),
    [locations]
  )

  const submit = async () => {
    if (!po || !warehouseId) {
      toast({ title: "Select warehouse location", variant: "destructive" })
      return
    }
    const lines = po.lines
      .map((l) => ({
        line_id: l.id,
        quantity: Number(qtyByLine[l.id] || 0),
      }))
      .filter((x) => x.quantity > 0)
    if (!lines.length) {
      toast({ title: "Enter quantity for at least one line", variant: "destructive" })
      return
    }
    try {
      await supplyChainApi.receiveGoods(po.id, {
        lines,
        warehouse_location_id: warehouseId,
      })
      toast({ title: "Goods received" })
      const r = await supplyChainApi.getPurchaseOrder(po.id)
      setPo(r.data)
    } catch (e: unknown) {
      const msg = e && typeof e === "object" && "response" in e ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail : null
      toast({ title: msg || "Receive failed", variant: "destructive" })
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <Button variant="ghost" size="sm" asChild className="mb-2 -ml-2">
          <Link to="/procurement/purchase-orders">← Purchase orders</Link>
        </Button>
        <h1 className="text-2xl font-semibold">Goods receipt (GRN)</h1>
        <p className="text-sm text-muted-foreground">Post receipt against an open PO. Stock uses InventoryService.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label>Purchase order</Label>
          <Select value={poId} onValueChange={setPoId}>
            <SelectTrigger>
              <SelectValue placeholder="Select PO" />
            </SelectTrigger>
            <SelectContent>
              {poList
                .filter((p) => ["sent", "acknowledged", "partial"].includes(p.status))
                .map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.po_number} ({p.status})
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Warehouse location</Label>
          <Select value={warehouseId} onValueChange={setWarehouseId}>
            <SelectTrigger>
              <SelectValue placeholder="Warehouse" />
            </SelectTrigger>
            <SelectContent>
              {warehouseLocations.map((l) => (
                <SelectItem key={l.id} value={l.id}>
                  {l.name} ({locKind(l)})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {warehouseLocations.length === 0 && (
        <p className="text-sm text-amber-700">
          No warehouse location found. Create one under Inventory → master data (type: warehouse).
        </p>
      )}

      {po && (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Line</TableHead>
                <TableHead className="text-right">Remaining</TableHead>
                <TableHead className="text-right w-36">Receive now</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {po.lines.map((l) => {
                const rem = l.quantity - l.received_quantity
                return (
                  <TableRow key={l.id}>
                    <TableCell className="font-mono text-xs">{l.material_id.slice(0, 8)}…</TableCell>
                    <TableCell className="text-right">{rem.toFixed(3)}</TableCell>
                    <TableCell className="text-right">
                      <Input
                        type="number"
                        className="text-right"
                        value={qtyByLine[l.id] ?? ""}
                        onChange={(e) => setQtyByLine((m) => ({ ...m, [l.id]: e.target.value }))}
                        min={0}
                        max={rem}
                        step="0.001"
                      />
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
          <Button onClick={submit}>Post receipt</Button>
        </>
      )}
    </div>
  )
}
