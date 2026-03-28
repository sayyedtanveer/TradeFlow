import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { supplyChainApi, type SubcontractOrderSummary, type Supplier } from "@/services/supply-chain.service"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
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
import { Plus } from "lucide-react"

export default function SubcontractListPage() {
  const { toast } = useToast()
  const [orders, setOrders] = useState<SubcontractOrderSummary[]>([])
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [open, setOpen] = useState(false)
  const [supplierId, setSupplierId] = useState("")
  const [productId, setProductId] = useState("")
  const [qty, setQty] = useState("1")

  const load = async () => {
    const [o, s] = await Promise.all([supplyChainApi.listSubcontractOrders(), supplyChainApi.listSuppliers()])
    setOrders(o.data)
    setSuppliers(s.data)
  }

  useEffect(() => {
    load().catch(() => toast({ title: "Failed to load", variant: "destructive" }))
  }, [toast])

  const create = async () => {
    if (!supplierId || !productId.trim()) {
      toast({ title: "Supplier and product (variant) UUID required", variant: "destructive" })
      return
    }
    try {
      await supplyChainApi.createSubcontractOrder({
        supplier_id: supplierId,
        product_id: productId.trim(),
        quantity: Number(qty),
      })
      toast({ title: "Subcontract order created" })
      setOpen(false)
      setProductId("")
      await load()
    } catch {
      toast({ title: "Create failed", variant: "destructive" })
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Subcontracting</h1>
          <p className="text-sm text-muted-foreground">Issue materials to subcontractor location, receive FG to warehouse.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New order
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>New subcontract order</DialogTitle>
            </DialogHeader>
            <div className="space-y-3 py-2">
              <div className="space-y-2">
                <Label>Supplier</Label>
                <Select value={supplierId} onValueChange={setSupplierId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Supplier" />
                  </SelectTrigger>
                  <SelectContent>
                    {suppliers.map((s) => (
                      <SelectItem key={s.id} value={s.id}>
                        {s.code} — {s.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Finished product (variant UUID)</Label>
                <Input value={productId} onChange={(e) => setProductId(e.target.value)} placeholder="item_variants.id" />
              </div>
              <div className="space-y-2">
                <Label>Quantity</Label>
                <Input type="number" value={qty} onChange={(e) => setQty(e.target.value)} />
              </div>
            </div>
            <DialogFooter>
              <Button onClick={create}>Create</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Order</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Qty</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {orders.map((o) => (
            <TableRow key={o.id}>
              <TableCell className="font-mono">{o.order_number}</TableCell>
              <TableCell>{o.status}</TableCell>
              <TableCell className="text-right">{o.quantity}</TableCell>
              <TableCell className="text-right">
                <Button variant="link" asChild>
                  <Link to={`/procurement/subcontract/${o.id}`}>Open</Link>
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {orders.length === 0 && <p className="text-sm text-muted-foreground">No subcontract orders.</p>}
    </div>
  )
}
