import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { REALTIME_EVENT_NAME } from "@/components/notifications/RealtimeNotificationsBridge"
import { materialService } from "@/services/material.service"
import {
  supplyChainApi,
  type RFQSummary,
  type SupplierQuotation,
} from "@/services/supply-chain.service"
import type { Material } from "@/types/material.types"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
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
    <div className="max-w-6xl space-y-6">
      <Button variant="ghost" size="sm" asChild>
        <Link to="/supplier-portal">{"<- Portal"}</Link>
      </Button>

      <div>
        <h1 className="text-2xl font-semibold">Quotations and RFQs</h1>
        <p className="text-sm text-muted-foreground">
          Respond to buyer RFQs and manage supplier quotation drafts/submissions.
        </p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <section className="rounded-xl border bg-card p-4 space-y-4">
        <h2 className="text-lg font-medium">Create quotation</h2>
        {materialError && (
          <Alert>
            <AlertDescription>
              Material lookup is unavailable for this supplier user. You can still respond to RFQs below.
            </AlertDescription>
          </Alert>
        )}
        <div className="grid gap-3 sm:grid-cols-4">
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
        <Button onClick={createQuotation}>Create quotation draft</Button>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Buyer RFQs</h2>
        {rfqs.length === 0 ? (
          <Alert>
            <AlertDescription>No RFQs are waiting for this supplier.</AlertDescription>
          </Alert>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>RFQ</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Deadline</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rfqs.map((rfq) => (
                <TableRow key={rfq.id}>
                  <TableCell className="font-mono">{rfq.rfq_number}</TableCell>
                  <TableCell>
                    <Badge variant="secondary">{rfq.status}</Badge>
                  </TableCell>
                  <TableCell>{rfq.deadline ?? "-"}</TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="secondary" onClick={() => respondToRfq(rfq)}>
                      Quote using price above
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Your quotations</h2>
        {quotations.length === 0 ? (
          <Alert>
            <AlertDescription>No quotations created yet.</AlertDescription>
          </Alert>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Quotation</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Material</TableHead>
                <TableHead className="text-right">Qty</TableHead>
                <TableHead className="text-right">Unit price</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {quotations.map((quotation) => (
                <TableRow key={quotation.id}>
                  <TableCell className="font-mono text-xs">
                    <Link to={`/supplier-portal/quotations/${quotation.id}`}>{quotation.id}</Link>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">{quotation.status}</Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{quotation.material_id}</TableCell>
                  <TableCell className="text-right">{quotation.quantity}</TableCell>
                  <TableCell className="text-right">{formatCurrency(quotation.unit_price)}</TableCell>
                  <TableCell className="text-right">
                    {quotation.status === "draft" && (
                      <Button size="sm" onClick={() => submitQuotation(quotation.id)}>
                        Submit
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </section>
    </div>
  )
}
