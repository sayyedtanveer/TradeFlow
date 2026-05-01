import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { supplyChainApi, type SupplierQuotation } from "@/services/supply-chain.service"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useToast } from "@/hooks/use-toast"

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(value)

export default function SupplierPortalQuotationDetailPage() {
  const { quotationId } = useParams<{ quotationId: string }>()
  const { toast } = useToast()
  const [quotation, setQuotation] = useState<SupplierQuotation | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadQuotation = async () => {
    if (!quotationId) return
    try {
      const response = await supplyChainApi.supplierGetQuotation(quotationId)
      setQuotation(response.data)
      setError(null)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || "Could not load quotation")
    }
  }

  useEffect(() => {
    void loadQuotation()
  }, [quotationId])

  const submitQuotation = async () => {
    if (!quotationId) return
    try {
      await supplyChainApi.supplierSubmitQuotation(quotationId)
      await loadQuotation()
      toast({ title: "Quotation submitted" })
    } catch (err: any) {
      toast({
        title: "Submit failed",
        description: err?.response?.data?.detail || err?.message,
        variant: "destructive",
      })
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      <Button variant="ghost" size="sm" asChild>
        <Link to="/supplier-portal/quotations">{"<- Quotations"}</Link>
      </Button>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {!quotation && !error && <p className="text-muted-foreground">Loading quotation...</p>}

      {quotation && (
        <section className="rounded-xl border bg-card p-5 space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h1 className="text-2xl font-semibold">Quotation</h1>
              <p className="font-mono text-xs text-muted-foreground">{quotation.id}</p>
            </div>
            <Badge variant="secondary">{quotation.status}</Badge>
          </div>
          <dl className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-sm text-muted-foreground">Material</dt>
              <dd className="font-mono text-sm">{quotation.material_id}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Linked PO</dt>
              <dd className="font-mono text-sm">{quotation.purchase_order_id ?? "-"}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Quantity</dt>
              <dd>{quotation.quantity}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Unit price</dt>
              <dd>{formatCurrency(quotation.unit_price)}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Valid until</dt>
              <dd>{quotation.valid_until ?? "-"}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Created</dt>
              <dd>{quotation.created_at ?? "-"}</dd>
            </div>
          </dl>
          {quotation.status === "draft" && <Button onClick={submitQuotation}>Submit quotation</Button>}
        </section>
      )}
    </div>
  )
}
