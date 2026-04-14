import { useEffect, useState } from "react"
import { supplyChainApi, type RFQDetail } from "@/services/supply-chain.service"
import { useToast } from "@/hooks/use-toast"
import { useParams, Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Award, Send, ArrowLeft } from "lucide-react"

type AwardDraft = {
  supplier_id: string
  expected_delivery: string
  notes: string
}

export default function RFQDetailPage() {
  const { rfqId } = useParams<{ rfqId: string }>()
  const { toast } = useToast()
  const [rfq, setRfq] = useState<RFQDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [awardDraft, setAwardDraft] = useState<AwardDraft>({
    supplier_id: "",
    expected_delivery: "",
    notes: "",
  })
  const [awarding, setAwarding] = useState(false)

  const load = async () => {
    if (!rfqId) return
    try {
      const r = await supplyChainApi.getRFQ(rfqId)
      setRfq(r.data)
    } catch {
      toast({ title: "Failed to load RFQ", variant: "destructive" })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [rfqId]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSend = async () => {
    if (!rfqId) return
    try {
      await supplyChainApi.sendRFQ(rfqId)
      toast({ title: "RFQ sent to all invited suppliers" })
      load()
    } catch (e: any) {
      toast({ title: e?.message ?? "Send failed", variant: "destructive" })
    }
  }

  const handleAward = async () => {
    if (!rfqId || !rfq || !awardDraft.supplier_id) return
    setAwarding(true)
    try {
      const lines = rfq.lines.map((l) => {
        const quote = rfq.quotation_details[awardDraft.supplier_id]
        return {
          material_id: l.material_id,
          quantity: l.quantity,
          unit_price: quote?.unit_price ?? 0,
        }
      })
      const res = await supplyChainApi.awardRFQ(rfqId, {
        supplier_id: awardDraft.supplier_id,
        lines,
        expected_delivery: awardDraft.expected_delivery || undefined,
        notes: awardDraft.notes || undefined,
      })
      toast({ title: `Awarded! PO ${res.data.po_number} created.` })
      load()
    } catch (e: any) {
      toast({ title: e?.message ?? "Award failed", variant: "destructive" })
    } finally {
      setAwarding(false)
    }
  }

  if (loading) return <div className="p-8 text-center text-muted-foreground">Loading…</div>
  if (!rfq) return <div className="p-8 text-center text-destructive">RFQ not found.</div>

  const respondedInvites = rfq.supplier_invites.filter((i) => i.status === "responded")

  return (
    <div className="space-y-6 p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button size="sm" variant="ghost" asChild>
          <Link to="/procurement/rfq"><ArrowLeft className="h-4 w-4" /></Link>
        </Button>
        <div className="flex-1">
          <h1 className="text-xl font-bold tracking-tight font-mono">{rfq.rfq_number}</h1>
          {rfq.title && <p className="text-sm text-muted-foreground">{rfq.title}</p>}
        </div>
        <Badge variant={rfq.status === "awarded" ? "default" : rfq.status === "sent" ? "secondary" : "outline"}>
          {rfq.status.toUpperCase()}
        </Badge>
        {rfq.status === "draft" && (
          <Button size="sm" onClick={handleSend} id="rfq-detail-send">
            <Send className="h-4 w-4 mr-1" /> Send to Suppliers
          </Button>
        )}
      </div>

      {/* Quotation comparison */}
      {rfq.status !== "draft" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Quotation Comparison</CardTitle>
            <CardDescription>
              {respondedInvites.length}/{rfq.supplier_invites.length} suppliers have responded.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Supplier</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Unit Price</TableHead>
                  <TableHead>Valid Until</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {rfq.supplier_invites.map((invite) => {
                  const q = rfq.quotation_details[invite.supplier_id]
                  return (
                    <TableRow key={invite.id}>
                      <TableCell className="text-sm font-medium">{invite.supplier_id.slice(0, 8)}…</TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            invite.status === "responded"
                              ? "default"
                              : invite.status === "declined"
                              ? "destructive"
                              : "secondary"
                          }
                          className="text-xs"
                        >
                          {invite.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {q ? `₹ ${q.unit_price.toFixed(2)}` : "—"}
                      </TableCell>
                      <TableCell className="text-sm">{q?.valid_until ?? "—"}</TableCell>
                      <TableCell className="text-right">
                        {rfq.status === "sent" && invite.status === "responded" && (
                          <Dialog>
                            <DialogTrigger asChild>
                              <Button
                                size="sm"
                                id={`award-btn-${invite.supplier_id}`}
                                onClick={() =>
                                  setAwardDraft((d) => ({ ...d, supplier_id: invite.supplier_id }))
                                }
                              >
                                <Award className="h-3 w-3 mr-1" /> Award
                              </Button>
                            </DialogTrigger>
                            <DialogContent>
                              <DialogHeader>
                                <DialogTitle>Award RFQ</DialogTitle>
                                <DialogDescription>
                                  This will create a Purchase Order for this supplier.
                                </DialogDescription>
                              </DialogHeader>
                              <div className="space-y-3">
                                <div className="space-y-1">
                                  <Label>Expected Delivery</Label>
                                  <Input
                                    type="date"
                                    value={awardDraft.expected_delivery}
                                    onChange={(e) =>
                                      setAwardDraft((d) => ({
                                        ...d,
                                        expected_delivery: e.target.value,
                                      }))
                                    }
                                  />
                                </div>
                                <div className="space-y-1">
                                  <Label>Notes</Label>
                                  <Input
                                    value={awardDraft.notes}
                                    onChange={(e) =>
                                      setAwardDraft((d) => ({ ...d, notes: e.target.value }))
                                    }
                                  />
                                </div>
                              </div>
                              <DialogFooter>
                                <Button
                                  id="confirm-award-btn"
                                  onClick={handleAward}
                                  disabled={awarding}
                                >
                                  {awarding ? "Processing…" : "Confirm Award & Create PO"}
                                </Button>
                              </DialogFooter>
                            </DialogContent>
                          </Dialog>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Awarded banner */}
      {rfq.status === "awarded" && rfq.awarded_po_id && (
        <Card className="border-emerald-200 bg-emerald-50 dark:bg-emerald-950/20">
          <CardContent className="pt-4 pb-4 flex items-center gap-3">
            <Award className="h-5 w-5 text-emerald-600" />
            <span className="text-sm">
              RFQ awarded.{" "}
              <Link
                to={`/procurement/purchase-orders/${rfq.awarded_po_id}`}
                className="underline font-medium text-emerald-700"
              >
                View Purchase Order →
              </Link>
            </span>
          </CardContent>
        </Card>
      )}

      {/* Lines */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Material Lines</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Material ID</TableHead>
                <TableHead className="text-right">Quantity</TableHead>
                <TableHead>Description</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rfq.lines.map((l) => (
                <TableRow key={l.id}>
                  <TableCell className="font-mono text-xs">{l.material_id.slice(0, 8)}…</TableCell>
                  <TableCell className="text-right">{l.quantity}</TableCell>
                  <TableCell className="text-muted-foreground text-sm">{l.description ?? "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
