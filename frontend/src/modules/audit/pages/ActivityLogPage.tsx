import { Fragment, useEffect, useState } from "react"
import { auditService, type AuditLogItem } from "@/services/audit.service"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useToast } from "@/hooks/use-toast"
import { RefreshCw, Search, ShieldCheck } from "lucide-react"

const PAGE_SIZE = 50

const formatDateTime = (value: string) => {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

const formatLabel = (value?: string | null) =>
  value ? value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase()) : "-"

const actorLabel = (item: AuditLogItem) => item.actor?.name || item.actor?.email || "System"

const sourceVariant = (source?: string | null) => (source === "business_event" ? "default" : "outline")

const summaryLabel = (item: AuditLogItem) =>
  item.summary || (typeof item.extra?.path === "string" ? item.extra.path : "-")

export default function ActivityLogPage() {
  const { toast } = useToast()
  const [items, setItems] = useState<AuditLogItem[]>([])
  const [total, setTotal] = useState(0)
  const [skip, setSkip] = useState(0)
  const [search, setSearch] = useState("")
  const [action, setAction] = useState("")
  const [entityType, setEntityType] = useState("")
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const load = async (nextSkip = skip) => {
    setLoading(true)
    try {
      const result = await auditService.getAuditLogs({
        search: search.trim() || undefined,
        action: action.trim() || undefined,
        entity_type: entityType.trim() || undefined,
        skip: nextSkip,
        limit: PAGE_SIZE,
      })
      setItems(result.items)
      setTotal(result.total)
      setSkip(result.skip)
    } catch (error: any) {
      toast({
        title: "Failed to load activity log",
        description: error?.response?.data?.detail || error?.message,
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load(0)
    // Load once on mount; filters are applied explicitly through the Search button.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const hasNext = skip + PAGE_SIZE < total
  const hasPrevious = skip > 0

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Activity Log</h1>
          <p className="text-muted-foreground">
            Tenant-wide audit trail for master data, procurement, supplier collaboration, GRN, and MRP events.
          </p>
        </div>
        <Button variant="outline" onClick={() => load(skip)} disabled={loading}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      <Alert>
        <ShieldCheck className="h-4 w-4" />
        <AlertTitle>ERP audit trail</AlertTitle>
        <AlertDescription>
          This page shows who performed each business step, when it happened, which document was affected, and
          before/after values when the operation captured them.
        </AlertDescription>
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="audit-search">Search</Label>
              <Input
                id="audit-search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="PO_SENT, supplier, rfq..."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="audit-action">Action</Label>
              <Input
                id="audit-action"
                value={action}
                onChange={(event) => setAction(event.target.value)}
                placeholder="PO_SENT"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="audit-entity">Entity type</Label>
              <Input
                id="audit-entity"
                value={entityType}
                onChange={(event) => setEntityType(event.target.value)}
                placeholder="purchase_order"
              />
            </div>
            <div className="flex items-end">
              <Button onClick={() => load(0)} disabled={loading} className="w-full">
                <Search className="mr-2 h-4 w-4" />
                Search
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Recent Activity</CardTitle>
          <span className="text-sm text-muted-foreground">
            Showing {items.length} of {total}
          </span>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead>Step</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Document</TableHead>
                  <TableHead>Summary</TableHead>
                  <TableHead>Source</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <Fragment key={item.id}>
                    <TableRow
                      className="cursor-pointer"
                      onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                    >
                      <TableCell className="whitespace-nowrap text-sm">{formatDateTime(item.occurred_at)}</TableCell>
                      <TableCell>
                        <div className="font-medium">{actorLabel(item)}</div>
                        {item.actor?.email && item.actor.name !== item.actor.email && (
                          <div className="text-xs text-muted-foreground">{item.actor.email}</div>
                        )}
                      </TableCell>
                      <TableCell>{item.business_step || formatLabel(item.entity_type)}</TableCell>
                      <TableCell>
                        <Badge variant="secondary">{item.action}</Badge>
                      </TableCell>
                      <TableCell>
                        <div>{item.document_no || item.entity_id || "-"}</div>
                        <div className="text-xs text-muted-foreground">{formatLabel(item.entity_type)}</div>
                      </TableCell>
                      <TableCell className="min-w-[240px]">{summaryLabel(item)}</TableCell>
                      <TableCell>
                        <Badge variant={sourceVariant(item.source)}>{formatLabel(item.source)}</Badge>
                      </TableCell>
                    </TableRow>
                    {expandedId === item.id && (
                      <TableRow>
                        <TableCell colSpan={7} className="bg-muted/40">
                          <div className="grid gap-4 md:grid-cols-2">
                            <div>
                              <div className="mb-2 text-xs font-semibold uppercase text-muted-foreground">
                                Before
                              </div>
                              <pre className="max-h-72 overflow-auto rounded-md bg-background p-3 text-xs">
                                {JSON.stringify(item.before_value || {}, null, 2)}
                              </pre>
                            </div>
                            <div>
                              <div className="mb-2 text-xs font-semibold uppercase text-muted-foreground">
                                After / Context
                              </div>
                              <pre className="max-h-72 overflow-auto rounded-md bg-background p-3 text-xs">
                                {JSON.stringify(item.after_value || item.extra || {}, null, 2)}
                              </pre>
                            </div>
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                ))}
                {!loading && items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                      No audit activity found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>

          <div className="mt-4 flex items-center justify-end gap-2">
            <Button variant="outline" disabled={!hasPrevious || loading} onClick={() => load(Math.max(0, skip - PAGE_SIZE))}>
              Previous
            </Button>
            <Button variant="outline" disabled={!hasNext || loading} onClick={() => load(skip + PAGE_SIZE)}>
              Next
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
