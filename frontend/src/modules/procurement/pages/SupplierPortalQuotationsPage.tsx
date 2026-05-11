import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Send } from "lucide-react"
import { REALTIME_EVENT_NAME } from "@/components/notifications/RealtimeNotificationsBridge"
import ResponsiveDataList from "@/components/shared/ResponsiveDataList"
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
import { useToast } from "@/hooks/use-toast"
import {
  SupplierPortalEmptyState,
  SupplierPortalHeader,
  SupplierPortalStatusBadge,
  SupplierPortalTabs,
} from "@/modules/procurement/components/SupplierPortalChrome"
import { materialService } from "@/services/material.service"
import {
  supplyChainApi,
  type RFQSummary,
  type SupplierQuotation,
} from "@/services/supply-chain.service"
import type { Material } from "@/types/material.types"

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(value)

export default function SupplierPortalQuotationsPage() {
  const { toast } = useToast()
  const [quotations, setQuotations] = useState<SupplierQuotation[]>([])
  const [rfqs, setRfqs] = useState<RFQSummary[]>([])
  const [materials, setMaterials] = useState<Material[]>([])
  const [materialId, setMaterialId] = useState("")
  const [quantity, setQuantity] = useState("1")
  const [unitPrice, setUnitPrice] = useState("0")
  const [validUntil, setValidUntil] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [materialError, setMaterialError] = useState<string | null>(null)

  const load = async (silent = false) => {
    try {
      const [quotationResponse, rfqResponse] = await Promise.all([
        supplyChainApi.supplierListQuotations(),
        supplyChainApi.supplierListRFQs(),
      ])
      setQuotations(quotationResponse.data)
      setRfqs(rfqResponse.data)
      setError(null)
      try {
        const materialResponse = await materialService.getMaterials({ page: 1, page_size: 200 })
        setMaterials(materialResponse.items)
        setMaterialError(null)
      } catch (err: any) {
        setMaterials([])
        setMaterialError(err?.response?.data?.detail || err?.message || "Material list unavailable")
      }
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || "Could not load quotations"
      setError(message)
      if (!silent) toast({ title: "Quotations unavailable", description: message, variant: "destructive" })
    }
  }

  useEffect(() => {
    void load()
  }, [])

  useEffect(() => {
    const handleRealtime = () => void load(true)
    window.addEventListener(REALTIME_EVENT_NAME, handleRealtime)
    return () => window.removeEventListener(REALTIME_EVENT_NAME, handleRealtime)
  }, [])

  const createQuotation = async () => {
    if (!materialId || Number(quantity) <= 0 || Number(unitPrice) <= 0) {
      toast({ title: "Material, quantity, and unit price are required", variant: "destructive" })
      return
    }
    try {
      await supplyChainApi.supplierQuotation({
        material_id: materialId,
        quantity: Number(quantity),
        unit_price: Number(unitPrice),
        valid_until: validUntil || undefined,
      })
      await load(true)
      toast({ title: "Quotation draft created" })
    } catch (err: any) {
      toast({
        title: "Quotation failed",
        description: err?.response?.data?.detail || err?.message,
        variant: "destructive",
      })
    }
  }

  const submitQuotation = async (id: string) => {
    try {
      await supplyChainApi.supplierSubmitQuotation(id)
      await load(true)
      toast({ title: "Quotation submitted" })
    } catch (err: any) {
      toast({
        title: "Submit failed",
        description: err?.response?.data?.detail || err?.message,
        variant: "destructive",
      })
    }
  }

  const respondToRfq = async (rfq: RFQSummary) => {
    const firstLine = rfq.lines?.[0]
    if (!firstLine) {
      toast({ title: "RFQ has no lines", variant: "destructive" })
      return
    }
    try {
      await supplyChainApi.supplierSubmitRFQQuote(rfq.id, {
        material_id: firstLine.material_id,
        quantity: firstLine.quantity,
        unit_price: Number(unitPrice || 0),
        valid_until: validUntil || undefined,
      })
      await load(true)
      toast({ title: "RFQ quotation submitted" })
    } catch (err: any) {
      toast({
        title: "RFQ response failed",
        description: err?.response?.data?.detail || err?.message,
        variant: "destructive",
      })
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-8">
      <SupplierPortalHeader
        eyebrow="Supplier workspace"
        title="Quotations and RFQs"
        description="Draft prices, answer buyer RFQs, and keep commercial responses moving without leaving the portal."
        backHref="/supplier-portal"
        backLabel="Portal"
        actions={
          <Button onClick={createQuotation} className="w-full sm:w-auto">
            <Send className="h-4 w-4" />
            Create quotation draft
          </Button>
        }
      />

      <div className="erp-portal-section space-y-4">
        <SupplierPortalTabs counts={{ quotations: quotations.length }} />
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </div>

      <section className="erp-portal-section space-y-4">
        <div className="space-y-1">
          <h2 className="text-xl font-semibold text-slate-950">Create quotation</h2>
          <p className="text-sm text-slate-600">Build a reusable quote first, then submit once the pricing is final.</p>
        </div>
        {materialError && (
          <Alert>
            <AlertDescription>
              Material lookup is unavailable for this supplier user. You can still respond to RFQs below.
            </AlertDescription>
          </Alert>
        )}
        <div className="grid gap-3 lg:grid-cols-4">
          <div className="space-y-2">
            <Label>Material</Label>
            <Select value={materialId} onValueChange={setMaterialId}>
              <SelectTrigger>
                <SelectValue placeholder="Select material" />
              </SelectTrigger>
              <SelectContent>
                {materials.map((material) => (
                  <SelectItem key={material.id} value={material.id}>
                    {material.code}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Quantity</Label>
            <Input type="number" value={quantity} onChange={(event) => setQuantity(event.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Unit price</Label>
            <Input type="number" value={unitPrice} onChange={(event) => setUnitPrice(event.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Valid until</Label>
            <Input type="date" value={validUntil} onChange={(event) => setValidUntil(event.target.value)} />
          </div>
        </div>
      </section>

      <section className="erp-portal-section space-y-4">
        <div className="space-y-1">
          <h2 className="text-xl font-semibold text-slate-950">Buyer RFQs</h2>
          <p className="text-sm text-slate-600">Use the unit price above, then submit a reply against the incoming buyer request.</p>
        </div>
        <ResponsiveDataList
          data={rfqs}
          getRowKey={(rfq) => rfq.id}
          emptyState={
            <SupplierPortalEmptyState
              title="No RFQs waiting"
              description="Buyer requests for quotation will appear here as soon as they are sent to your supplier account."
              actionHref="/supplier-portal"
              actionLabel="Back to portal"
            />
          }
          columns={[
            {
              key: "rfq",
              header: "RFQ",
              cell: (rfq) => (
                <div>
                  <p className="font-mono text-sm font-semibold text-slate-900">{rfq.rfq_number}</p>
                  <p className="text-xs text-slate-500">{rfq.title ?? "Buyer quotation request"}</p>
                </div>
              ),
            },
            {
              key: "status",
              header: "Status",
              cell: (rfq) => <SupplierPortalStatusBadge status={rfq.status} />,
            },
            {
              key: "deadline",
              header: "Deadline",
              cell: (rfq) => rfq.deadline ?? "-",
            },
            {
              key: "action",
              header: "Action",
              headerClassName: "text-right",
              className: "text-right",
              cell: (rfq) => (
                <Button size="sm" variant="secondary" onClick={() => respondToRfq(rfq)}>
                  Quote using price above
                </Button>
              ),
            },
          ]}
          renderMobileCard={(rfq) => (
            <article className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <p className="font-mono text-sm font-semibold text-slate-900">{rfq.rfq_number}</p>
                  <p className="text-sm text-slate-500">{rfq.deadline ?? "No deadline set"}</p>
                </div>
                <SupplierPortalStatusBadge status={rfq.status} />
              </div>
              <Button className="mt-4 w-full" size="sm" variant="secondary" onClick={() => respondToRfq(rfq)}>
                Quote using price above
              </Button>
            </article>
          )}
        />
      </section>

      <section className="erp-portal-section space-y-4">
        <div className="space-y-1">
          <h2 className="text-xl font-semibold text-slate-950">Your quotations</h2>
          <p className="text-sm text-slate-600">Track drafts, submit ready quotes, and review their commercial details.</p>
        </div>
        <ResponsiveDataList
          data={quotations}
          getRowKey={(quotation) => quotation.id}
          emptyState={
            <SupplierPortalEmptyState
              title="No quotations created yet"
              description="Create a draft above to start sharing prices with the buyer."
              actionHref="/supplier-portal"
              actionLabel="Return to portal"
            />
          }
          columns={[
            {
              key: "quotation",
              header: "Quotation",
              cell: (quotation) => (
                <div>
                  <Link to={`/supplier-portal/quotations/${quotation.id}`} className="font-mono text-xs text-blue-700 hover:underline">
                    {quotation.quotation_number}
                  </Link>
                  <p className="mt-1 text-xs text-slate-500">{quotation.material_code} — {quotation.material_name}</p>
                </div>
              ),
            },
            {
              key: "status",
              header: "Status",
              cell: (quotation) => <SupplierPortalStatusBadge status={quotation.status} />,
            },
            {
              key: "qty",
              header: "Qty",
              headerClassName: "text-right",
              className: "text-right",
              cell: (quotation) => quotation.quantity,
            },
            {
              key: "price",
              header: "Unit price",
              headerClassName: "text-right",
              className: "text-right",
              cell: (quotation) => formatCurrency(quotation.unit_price),
            },
            {
              key: "action",
              header: "Action",
              headerClassName: "text-right",
              className: "text-right",
              cell: (quotation) =>
                quotation.status === "draft" ? (
                  <Button size="sm" onClick={() => submitQuotation(quotation.id)}>
                    Submit
                  </Button>
                ) : (
                  <Button size="sm" variant="outline" asChild>
                    <Link to={`/supplier-portal/quotations/${quotation.id}`}>Open</Link>
                  </Button>
                ),
            },
          ]}
          renderMobileCard={(quotation) => (
            <article className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <Link to={`/supplier-portal/quotations/${quotation.id}`} className="font-mono text-xs text-blue-700 hover:underline">
                    {quotation.id}
                  </Link>
                  <p className="text-sm text-slate-500">{quotation.material_id}</p>
                </div>
                <SupplierPortalStatusBadge status={quotation.status} />
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-slate-500">Quantity</p>
                  <p className="font-semibold text-slate-900">{quotation.quantity}</p>
                </div>
                <div>
                  <p className="text-slate-500">Unit price</p>
                  <p className="font-semibold text-slate-900">{formatCurrency(quotation.unit_price)}</p>
                </div>
              </div>
              <div className="mt-4 grid gap-2">
                {quotation.status === "draft" && (
                  <Button size="sm" className="w-full" onClick={() => submitQuotation(quotation.id)}>
                    Submit
                  </Button>
                )}
                <Button size="sm" variant="outline" className="w-full" asChild>
                  <Link to={`/supplier-portal/quotations/${quotation.id}`}>Open quotation</Link>
                </Button>
              </div>
            </article>
          )}
        />
      </section>
    </div>
  )
}
