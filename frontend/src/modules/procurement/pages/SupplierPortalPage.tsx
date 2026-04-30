import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { supplyChainApi } from "@/services/supply-chain.service"
import { materialService } from "@/services/material.service"
import type { Material } from "@/types/material.types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
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

const normalizeStatus = (status: string) => status.trim().toLowerCase()

export default function SupplierPortalPage() {
  const { toast } = useToast()
  const [rows, setRows] = useState<PoRow[]>([])
  const [materials, setMaterials] = useState<Material[]>([])
  const [isMaterialsLoading, setIsMaterialsLoading] = useState(false)
  const [materialsError, setMaterialsError] = useState<string | null>(null)
  const [hasRequestedMaterials, setHasRequestedMaterials] = useState(false)
  const [poForQuote, setPoForQuote] = useState<string>("none")
  const [matId, setMatId] = useState("")
  const [qQty, setQQty] = useState("1")
  const [qPrice, setQPrice] = useState("0")
  const [validUntil, setValidUntil] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const normalizedStatuses = rows.map((row) => normalizeStatus(row.status))
  const totalPos = rows.length
  const awaitingAcknowledgement = normalizedStatuses.filter((status) => status === "sent").length
  const activePos = normalizedStatuses.filter((status) => !["completed", "cancelled", "closed"].includes(status)).length
  const totalOrderValue = rows.reduce((sum, row) => sum + row.total_amount, 0)

  const load = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const r = await supplyChainApi.supplierPortalPOs()
      setRows((r.data?.items ?? []) as PoRow[])
    } catch (err: any) {
      console.error("supplierPortal load error:", err)
      console.error("[SupplierPortal] Status:", err?.response?.status, "Data:", err?.response?.data)
      const message = err?.response?.data?.detail || err?.message || "Failed to load purchase orders"
      setError(message)
      toast({
        title: "Portal unavailable",
        description: message,
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  const loadMaterials = async () => {
    if (hasRequestedMaterials || isMaterialsLoading) {
      return
    }

    try {
      setHasRequestedMaterials(true)
      setIsMaterialsLoading(true)
      setMaterialsError(null)
      const response = await materialService.getMaterials({ page: 1, page_size: 200 })
      setMaterials(response.items)
    } catch (err: any) {
      console.error("materials load error:", err)
      const message = err?.response?.data?.detail || err?.message || "Failed to load materials"
      setMaterialsError(message)
    } finally {
      setIsMaterialsLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const ack = async (id: string) => {
    try {
      await supplyChainApi.supplierAckPO(id)
      await load()
      toast({ title: "Acknowledged" })
    } catch {
      console.error("ack error for id:", id)
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
      console.error("submitQuote error")
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

      {!error && (
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl border bg-card p-4">
            <p className="text-sm text-muted-foreground">Total purchase orders</p>
            <p className="mt-2 text-2xl font-semibold">{isLoading ? "..." : totalPos}</p>
          </div>
          <div className="rounded-xl border bg-card p-4">
            <p className="text-sm text-muted-foreground">Active orders</p>
            <p className="mt-2 text-2xl font-semibold">{isLoading ? "..." : activePos}</p>
          </div>
          <div className="rounded-xl border bg-card p-4">
            <p className="text-sm text-muted-foreground">Awaiting acknowledgement</p>
            <p className="mt-2 text-2xl font-semibold">{isLoading ? "..." : awaitingAcknowledgement}</p>
          </div>
          <div className="rounded-xl border bg-card p-4">
            <p className="text-sm text-muted-foreground">Portfolio value</p>
            <p className="mt-2 text-2xl font-semibold">{isLoading ? "..." : totalOrderValue.toFixed(2)}</p>
          </div>
        </section>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertDescription>
            <strong>Error:</strong> {error}
            <p className="text-xs mt-2">Contact your system administrator to link your account to a supplier.</p>
          </AlertDescription>
        </Alert>
      )}

      {isLoading && !error && (
        <Alert>
          <AlertDescription>Loading your purchase orders...</AlertDescription>
        </Alert>
      )}

      {!isLoading && !error && rows.length === 0 && (
        <Alert>
          <AlertDescription>No purchase orders assigned to you yet.</AlertDescription>
        </Alert>
      )}

      {!error && (
        <>
          <section>
            <h2 className="font-medium mb-2">Your purchase orders</h2>
            {isLoading ? (
              <p className="text-sm text-muted-foreground">Loading...</p>
            ) : rows.length === 0 ? (
              <p className="text-sm text-muted-foreground">No purchase orders assigned to you.</p>
            ) : (
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
                        {normalizeStatus(p.status) === "sent" && (
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
            )}
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
          <Select
            value={matId}
            onValueChange={setMatId}
            onOpenChange={(open) => {
              if (open) {
                void loadMaterials()
              }
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder="Material" />
            </SelectTrigger>
            <SelectContent>
              {isMaterialsLoading && (
                <SelectItem value="__loading" disabled>
                  Loading materials...
                </SelectItem>
              )}
              {!isMaterialsLoading && materials.length > 0 && materials.map((m) => (
                <SelectItem key={m.id} value={m.id}>
                  {m.code}
                </SelectItem>
              ))}
              {!isMaterialsLoading && materials.length === 0 && materialsError && (
                <SelectItem value="__unavailable" disabled>
                  Materials unavailable
                </SelectItem>
              )}
              {!isMaterialsLoading && materials.length === 0 && !materialsError && hasRequestedMaterials && (
                <SelectItem value="__empty" disabled>
                  No materials found
                </SelectItem>
              )}
              {!isMaterialsLoading && materials.length === 0 && !hasRequestedMaterials && (
                <SelectItem value="__lazyload" disabled>
                  Open to load materials
                </SelectItem>
              )}
            </SelectContent>
          </Select>
          {materialsError && <p className="text-xs text-destructive">{materialsError}</p>}
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
        </>
      )}
    </div>
  )
}
