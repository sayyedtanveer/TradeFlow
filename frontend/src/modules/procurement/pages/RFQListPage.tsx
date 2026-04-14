import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { supplyChainApi, type RFQSummary } from "@/services/supply-chain.service"
import { useToast } from "@/hooks/use-toast"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { FileText, Plus, Send, CheckCircle2, Clock, Award } from "lucide-react"

const STATUS_META: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline"; icon: React.ReactNode }> = {
  draft:   { label: "Draft",   variant: "secondary",    icon: <Clock className="h-3 w-3" /> },
  sent:    { label: "Sent",    variant: "default",      icon: <Send className="h-3 w-3" /> },
  closed:  { label: "Closed",  variant: "outline",      icon: <CheckCircle2 className="h-3 w-3" /> },
  awarded: { label: "Awarded", variant: "default",      icon: <Award className="h-3 w-3" /> },
}

export default function RFQListPage() {
  const { toast } = useToast()
  const [rfqs, setRfqs] = useState<RFQSummary[]>([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const r = await supplyChainApi.listRFQs()
      setRfqs(r.data)
    } catch {
      toast({ title: "Failed to load RFQs", variant: "destructive" })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSend = async (id: string) => {
    try {
      await supplyChainApi.sendRFQ(id)
      toast({ title: "RFQ sent to suppliers" })
      load()
    } catch (e: any) {
      toast({ title: e?.message ?? "Send failed", variant: "destructive" })
    }
  }

  const stats = {
    total: rfqs.length,
    draft: rfqs.filter((r) => r.status === "draft").length,
    sent: rfqs.filter((r) => r.status === "sent").length,
    awarded: rfqs.filter((r) => r.status === "awarded").length,
  }

  return (
    <div className="space-y-6 p-6 max-w-7xl mx-auto">
      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Request for Quotation</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage RFQs — send to multiple suppliers and compare quotations.
          </p>
        </div>
        <Button asChild id="rfq-create-btn">
          <Link to="/procurement/rfq/new">
            <Plus className="h-4 w-4 mr-2" />
            Create RFQ
          </Link>
        </Button>
      </div>

      {/* ── Stats ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total", value: stats.total, color: "text-foreground" },
          { label: "Draft", value: stats.draft, color: "text-muted-foreground" },
          { label: "Sent", value: stats.sent, color: "text-blue-600" },
          { label: "Awarded", value: stats.awarded, color: "text-emerald-600" },
        ].map((s) => (
          <Card key={s.label} className="border">
            <CardHeader className="pb-2 pt-4 px-4">
              <CardDescription className="text-xs uppercase tracking-wide">{s.label}</CardDescription>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <span className={`text-2xl font-bold ${s.color}`}>{s.value}</span>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* ── Table ── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="h-4 w-4" /> All RFQs
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center text-muted-foreground text-sm">Loading…</div>
          ) : rfqs.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground text-sm">
              No RFQs yet. Create one to get started.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>RFQ #</TableHead>
                  <TableHead>Title</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Lines</TableHead>
                  <TableHead>Suppliers</TableHead>
                  <TableHead>Responded</TableHead>
                  <TableHead>Deadline</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {rfqs.map((rfq) => {
                  const meta = STATUS_META[rfq.status] ?? STATUS_META.draft
                  const responded = rfq.supplier_invites.filter((i) => i.status === "responded").length
                  return (
                    <TableRow key={rfq.id}>
                      <TableCell className="font-mono text-sm">{rfq.rfq_number}</TableCell>
                      <TableCell className="max-w-[200px] truncate">
                        {rfq.title ?? <span className="text-muted-foreground">—</span>}
                      </TableCell>
                      <TableCell>
                        <Badge variant={meta.variant} className="gap-1 text-xs">
                          {meta.icon} {meta.label}
                        </Badge>
                      </TableCell>
                      <TableCell>{rfq.lines?.length ?? "—"}</TableCell>
                      <TableCell>{rfq.supplier_invites.length}</TableCell>
                      <TableCell>
                        <span className={responded > 0 ? "text-emerald-600 font-medium" : "text-muted-foreground"}>
                          {responded} / {rfq.supplier_invites.length}
                        </span>
                      </TableCell>
                      <TableCell className="text-sm">
                        {rfq.deadline ?? <span className="text-muted-foreground">—</span>}
                      </TableCell>
                      <TableCell className="text-right space-x-2">
                        {rfq.status === "draft" && (
                          <Button
                            size="sm"
                            variant="outline"
                            id={`rfq-send-${rfq.id}`}
                            onClick={() => handleSend(rfq.id)}
                          >
                            <Send className="h-3 w-3 mr-1" /> Send
                          </Button>
                        )}
                        <Button size="sm" variant="link" asChild>
                          <Link to={`/procurement/rfq/${rfq.id}`}>View</Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
