import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { supplyChainApi } from "@/services/supply-chain.service"
import { materialService } from "@/services/material.service"
import type { Material } from "@/types/material.types"
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

type PoRow = { id: string; po_number: string; status: string; total_amount: number }

export default function SupplierPortalPage() {
  const { toast } = useToast()
  const [rows, setRows] = useState<PoRow[]>([])
  const [materials, setMaterials] = useState<Material[]>([])
  const [poForQuote, setPoForQuote] = useState<string>("none")
  const [matId, setMatId] = useState("")
  const [qQty, setQQty] = useState("1")
  const [qPrice, setQPrice] = useState("0")
  const [validUntil, setValidUntil] = useState("")

  const load = () =>
    supplyChainApi.supplierPortalPOs().then((r) => setRows(r.data as PoRow[]))

  useEffect(() => {
    load().catch(() =>
      toast({
        title: "Portal unavailable",
        description: "Log in as a user linked to a supplier (supplier_id).",
        variant: "destructive",
      })
    )
    materialService.getMaterials({ page: 1, page_size: 200 }).then((m) => setMaterials(m.items))
  }, [toast])

  const ack = async (id: string) => {
    try {
      await supplyChainApi.supplierAckPO(id)
      await load()
      toast({ title: "Acknowledged" })
    } catch {
      toast({ title: "Failed", variant: "destructive" })
    }
  }

  const submitQuote = async () => {
    if (!matId || !qPrice) {
      toast({ title: "Material and unit price required", variant: "destructive" })
      return
    }
    try {
      await supplyChainApi.supplierQuotation({
        material_id: matId,
        quantity: Number(qQty),
        unit_price: Number(qPrice),
        valid_until: validUntil || undefined,
        purchase_order_id: poForQuote !== "none" ? poForQuote : undefined,
      })
      toast({ title: "Quotation submitted" })
    } catch {
      toast({ title: "Submit failed", variant: "destructive" })
    }
  }

  return (
    <div className="space-y-8 max-w-4xl">
      <div>
        <h1 className="text-2xl font-semibold">Supplier portal</h1>
        <p className="text-sm text-muted-foreground">
          View your POs, acknowledge, and submit quotations. Requires supplier-linked account.
        </p>
      </div>

      <section>
        <h2 className="font-medium mb-2">Your purchase orders</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>PO</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((p) => (
              <TableRow key={p.id}>
                <TableCell className="font-mono">{p.po_number}</TableCell>
                <TableCell>{p.status}</TableCell>
                <TableCell className="text-right">{p.total_amount.toFixed(2)}</TableCell>
                <TableCell className="text-right space-x-2">
                  {p.status === "sent" && (
                    <Button size="sm" variant="secondary" onClick={() => ack(p.id)}>
                      Acknowledge
                    </Button>
                  )}
                  <Button size="sm" variant="link" asChild>
                    <Link to={`/supplier-portal/po/${p.id}`}>Details</Link>
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {rows.length === 0 && <p className="text-sm text-muted-foreground">No purchase orders.</p>}
      </section>

      <section className="border rounded-lg p-4 space-y-3 max-w-lg">
        <h2 className="font-medium">Submit quotation</h2>
        <div className="space-y-2">
          <Label>Optional: link to PO</Label>
          <Select value={poForQuote} onValueChange={setPoForQuote}>
            <SelectTrigger>
              <SelectValue placeholder="None" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">No linked PO</SelectItem>
              {rows.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.po_number}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Material</Label>
          <Select value={matId} onValueChange={setMatId}>
            <SelectTrigger>
              <SelectValue placeholder="Material" />
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
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-2">
            <Label>Quantity</Label>
            <Input type="number" value={qQty} onChange={(e) => setQQty(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Unit price</Label>
            <Input type="number" value={qPrice} onChange={(e) => setQPrice(e.target.value)} />
          </div>
        </div>
        <div className="space-y-2">
          <Label>Valid until</Label>
          <Input type="date" value={validUntil} onChange={(e) => setValidUntil(e.target.value)} />
        </div>
        <Button onClick={submitQuote}>Submit quotation</Button>
      </section>
    </div>
  )
}
