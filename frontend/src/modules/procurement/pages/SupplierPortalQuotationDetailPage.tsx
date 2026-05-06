import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { Send } from "lucide-react"
import { supplyChainApi, type SupplierQuotation } from "@/services/supply-chain.service"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { useToast } from "@/hooks/use-toast"
import {
  SupplierPortalHeader,
  SupplierPortalStatusBadge,
  SupplierPortalTabs,
} from "@/modules/procurement/components/SupplierPortalChrome"

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
    <div className="mx-auto max-w-5xl space-y-6 pb-8">
      <SupplierPortalHeader
        eyebrow="Supplier workspace"
        title="Quotation detail"
        description="Review the selected quotation before sending it to the buyer."
        backHref="/supplier-portal/quotations"
        backLabel="Quotations"
        actions={
          quotation?.status === "draft" ? (
            <Button onClick={submitQuotation} className="w-full sm:w-auto">
              <Send className="h-4 w-4" />
              Submit quotation
            </Button>
          ) : undefined
        }
      />

      <div className="erp-portal-section space-y-4">
        <SupplierPortalTabs />
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </div>

      {!quotation && !error && <p className="text-sm text-muted-foreground">Loading quotation...</p>}

      {quotation && (
        <section className="erp-portal-section space-y-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="space-y-2">
              <p className="font-mono text-sm text-slate-500">{quotation.id}</p>
              <SupplierPortalStatusBadge status={quotation.status} />
            </div>
            <div className="rounded-[24px] border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              Share the quote once the numbers and validity period are final.
            </div>
          </div>
          <dl className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-[22px] border border-slate-200 bg-slate-50 p-4">
              <dt className="text-sm text-slate-500">Material</dt>
              <dd className="mt-1 font-mono text-sm text-slate-900">{quotation.material_id}</dd>
            </div>
            <div className="rounded-[22px] border border-slate-200 bg-slate-50 p-4">
              <dt className="text-sm text-slate-500">Linked PO</dt>
              <dd className="mt-1 font-mono text-sm text-slate-900">{quotation.purchase_order_id ?? "-"}</dd>
            </div>
            <div className="rounded-[22px] border border-slate-200 bg-slate-50 p-4">
              <dt className="text-sm text-slate-500">Quantity</dt>
              <dd className="mt-1 text-lg font-semibold text-slate-900">{quotation.quantity}</dd>
            </div>
            <div className="rounded-[22px] border border-slate-200 bg-slate-50 p-4">
              <dt className="text-sm text-slate-500">Unit price</dt>
              <dd className="mt-1 text-lg font-semibold text-slate-900">{formatCurrency(quotation.unit_price)}</dd>
            </div>
            <div className="rounded-[22px] border border-slate-200 bg-slate-50 p-4">
              <dt className="text-sm text-slate-500">Valid until</dt>
              <dd className="mt-1 text-slate-900">{quotation.valid_until ?? "-"}</dd>
            </div>
            <div className="rounded-[22px] border border-slate-200 bg-slate-50 p-4">
              <dt className="text-sm text-slate-500">Created</dt>
              <dd className="mt-1 text-slate-900">{quotation.created_at ?? "-"}</dd>
            </div>
          </dl>
        </section>
      )}
    </div>
  )
}
