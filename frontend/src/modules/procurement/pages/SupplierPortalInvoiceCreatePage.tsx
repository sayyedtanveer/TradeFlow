import { useEffect, useMemo, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { supplyChainApi, type PurchaseOrder } from "@/services/supply-chain.service"
import { Alert, AlertDescription } from "@/components/ui/alert"
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
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/hooks/use-toast"

const today = () => new Date().toISOString().slice(0, 10)
const plusDays = (days: number) => {
  const date = new Date()
  date.setDate(date.getDate() + days)
  return date.toISOString().slice(0, 10)
}

export default function SupplierPortalInvoiceCreatePage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([])
  const [poId, setPoId] = useState("")
  const [supplierRef, setSupplierRef] = useState("")
  const [invoiceDate, setInvoiceDate] = useState(today())
  const [dueDate, setDueDate] = useState(plusDays(30))
  const [subtotal, setSubtotal] = useState("0")
  const [taxAmount, setTaxAmount] = useState("0")
  const [notes, setNotes] = useState("")
  const [error, setError] = useState<string | null>(null)
  const grandTotal = useMemo(() => Number(subtotal || 0) + Number(taxAmount || 0), [subtotal, taxAmount])

  useEffect(() => {
    const loadPurchaseOrders = async () => {
      try {
        const response = await supplyChainApi.supplierPortalPOs({ limit: 200 })
        setPurchaseOrders(response.data.items)
      } catch (err: any) {
        setError(err?.response?.data?.detail || err?.message || "Could not load purchase orders")
      }
    }
    void loadPurchaseOrders()
  }, [])

  const selectedPo = purchaseOrders.find((po) => po.id === poId)

  const usePoTotal = () => {
    if (!selectedPo) return
    setSubtotal(String(selectedPo.total_amount))
    setTaxAmount("0")
  }

  const submitInvoice = async () => {
    if (!invoiceDate || !dueDate || Number(subtotal) <= 0 || grandTotal <= 0) {
      toast({ title: "Invoice date, due date, and positive amount are required", variant: "destructive" })
      return
    }

    try {
      await supplyChainApi.supplierCreateInvoice({
        purchase_order_id: poId || undefined,
        supplier_invoice_ref: supplierRef || undefined,
        invoice_date: invoiceDate,
        due_date: dueDate,
        subtotal: Number(subtotal),
        tax_amount: Number(taxAmount || 0),
        grand_total: grandTotal,
        notes: notes || undefined,
      })
      toast({ title: "Invoice submitted" })
      navigate("/supplier-portal/invoices")
    } catch (err: any) {
      toast({
        title: "Invoice submission failed",
        description: err?.response?.data?.detail || err?.message,
        variant: "destructive",
      })
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      <Button variant="ghost" size="sm" asChild>
        <Link to="/supplier-portal/invoices">{"<- Invoices"}</Link>
      </Button>

      <div>
        <h1 className="text-2xl font-semibold">Submit supplier invoice</h1>
        <p className="text-sm text-muted-foreground">
          Link the invoice to an acknowledged or received purchase order when available.
        </p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <section className="rounded-xl border bg-card p-4 space-y-4">
        <div className="space-y-2">
          <Label>Purchase order</Label>
          <Select value={poId || "none"} onValueChange={(value) => setPoId(value === "none" ? "" : value)}>
            <SelectTrigger>
              <SelectValue placeholder="Optional PO" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">No linked PO</SelectItem>
              {purchaseOrders.map((po) => (
                <SelectItem key={po.id} value={po.id}>
                  {po.po_number} - {po.status}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {selectedPo && (
            <Button type="button" size="sm" variant="secondary" onClick={usePoTotal}>
              Use PO total
            </Button>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label>Supplier invoice reference</Label>
            <Input value={supplierRef} onChange={(event) => setSupplierRef(event.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Invoice date</Label>
            <Input type="date" value={invoiceDate} onChange={(event) => setInvoiceDate(event.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Due date</Label>
            <Input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Subtotal</Label>
            <Input type="number" value={subtotal} onChange={(event) => setSubtotal(event.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Tax amount</Label>
            <Input type="number" value={taxAmount} onChange={(event) => setTaxAmount(event.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Grand total</Label>
            <Input value={grandTotal.toFixed(2)} readOnly />
          </div>
        </div>

        <div className="space-y-2">
          <Label>Notes</Label>
          <Textarea value={notes} onChange={(event) => setNotes(event.target.value)} />
        </div>
        <Button onClick={submitInvoice}>Submit invoice</Button>
      </section>
    </div>
  )
}
