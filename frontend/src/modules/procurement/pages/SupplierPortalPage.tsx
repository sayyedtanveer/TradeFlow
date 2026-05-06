import { type ComponentProps, useCallback, useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import {
  ClipboardClock,
  FileSpreadsheet,
  HandCoins,
  PackageCheck,
  ScrollText,
  SendToBack,
  type LucideIcon,
} from "lucide-react"
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
  SupplierPortalAlertBanner,
  SupplierPortalEmptyState,
  SupplierPortalHeader,
  SupplierPortalKpiCard,
  SupplierPortalStatusBadge,
  SupplierPortalTabs,
} from "@/modules/procurement/components/SupplierPortalChrome"
import { materialService } from "@/services/material.service"
import { supplyChainApi, type SupplierDashboard } from "@/services/supply-chain.service"
import type { Material } from "@/types/material.types"
import { cn } from "@/lib/utils"

type PoRow = { id: string; po_number: string; status: string; total_amount: number }
type SupplierPortalAction = {
  label: string
  helper: string
  href: string
  icon: LucideIcon
  variant?: ComponentProps<typeof Button>["variant"]
}

const normalizeStatus = (status: string) => status.trim().toLowerCase()
const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(value)

const primaryActions: SupplierPortalAction[] = [
  {
    label: "Submit quotation",
    helper: "Respond to RFQs",
    href: "/supplier-portal/quotations",
    icon: SendToBack,
  },
  {
    label: "Upload invoice",
    helper: "Bill completed deliveries",
    href: "/supplier-portal/invoices/new",
    icon: ScrollText,
    variant: "outline",
  },
  {
    label: "View pending POs",
    helper: "Check buyer orders",
    href: "#supplier-purchase-orders",
    icon: ClipboardClock,
    variant: "outline",
  },
]

function SupplierPortalPrimaryActions({ compact = false }: { compact?: boolean }) {
  return (
    <div
      className={cn(
        "w-full min-w-0 gap-3",
        compact
          ? "flex max-w-full overflow-x-auto pb-1 md:grid md:grid-cols-3 md:overflow-visible md:pb-0 xl:w-auto"
          : "grid md:grid-cols-3 2xl:min-w-[34rem]"
      )}
    >
      {primaryActions.map((action, index) => {
        const Icon = action.icon
        const actionLabel = (
          <>
            <Icon className="h-4 w-4" />
            {action.label}
          </>
        )

        return (
          <div key={action.label} className={cn("min-w-0 space-y-1", compact && "min-w-[9.5rem] md:min-w-0")}>
            <Button
              asChild
              variant={action.variant}
              size={compact ? "default" : "lg"}
              className={cn(
                "w-full justify-center transition-all duration-200",
                !compact && "h-11",
                compact && "h-10 px-3 text-xs sm:text-sm",
                index === 0 && "shadow-md"
              )}
            >
              {action.href.startsWith("#") ? (
                <a href={action.href}>{actionLabel}</a>
              ) : (
                <Link to={action.href}>{actionLabel}</Link>
              )}
            </Button>
            <p
              className={cn(
                "px-1 text-xs leading-4 text-slate-600",
                compact && "hidden xl:block"
              )}
            >
              {action.helper}
            </p>
          </div>
        )
      })}
    </div>
  )
}

export default function SupplierPortalPage() {
  const { toast } = useToast()
  const [rows, setRows] = useState<PoRow[]>([])
  const [dashboard, setDashboard] = useState<SupplierDashboard | null>(null)
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
  const totalPos = dashboard?.purchase_orders.total ?? rows.length
  const awaitingAcknowledgement =
    dashboard?.purchase_orders.by_status.sent ??
    normalizedStatuses.filter((status) => status === "sent").length
  const activePos = normalizedStatuses.filter((status) => !["completed", "cancelled", "closed"].includes(status)).length
  const totalOrderValue = rows.reduce((sum, row) => sum + row.total_amount, 0)
  const overdueInvoices = dashboard?.invoices.by_status.overdue ?? 0
  const outstandingValue = dashboard?.invoices.outstanding ?? 0

  const load = useCallback(
    async (silent = false) => {
      try {
        if (!silent) setIsLoading(true)
        setError(null)
        const [poResponse, dashboardResponse] = await Promise.all([
          supplyChainApi.supplierPortalPOs(),
          supplyChainApi.supplierDashboard(),
        ])
        setRows((poResponse.data?.items ?? []) as PoRow[])
        setDashboard(dashboardResponse.data)
      } catch (err: any) {
        console.error("supplierPortal load error:", err)
        console.error("[SupplierPortal] Status:", err?.response?.status, "Data:", err?.response?.data)
        const message = err?.response?.data?.detail || err?.message || "Failed to load purchase orders"
        setError(message)
        if (!silent) {
          toast({
            title: "Portal unavailable",
            description: message,
            variant: "destructive",
          })
        }
      } finally {
        if (!silent) setIsLoading(false)
      }
    },
    [toast]
  )

  const loadMaterials = async () => {
    if (hasRequestedMaterials || isMaterialsLoading) return

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
  }, [load])

  useEffect(() => {
    const handleRealtime = () => {
      void load(true)
    }
    window.addEventListener(REALTIME_EVENT_NAME, handleRealtime)
    return () => window.removeEventListener(REALTIME_EVENT_NAME, handleRealtime)
  }, [load])

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

  const tabCounts = useMemo(
    () => ({
      purchaseOrders: totalPos,
      quotations: dashboard?.quotations.total ?? 0,
      receipts: dashboard?.receipts.pending ?? 0,
      invoices: dashboard?.invoices.total ?? 0,
    }),
    [dashboard, totalPos]
  )

  const recentActionCards = dashboard?.action_items ?? []

  return (
    <div className="mx-auto w-full max-w-7xl min-w-0 space-y-5 overflow-x-clip pb-8">
      <SupplierPortalHeader
        eyebrow="Supplier workspace"
        title={dashboard?.supplier.name ? `${dashboard.supplier.name} command center` : "Supplier portal"}
        description="Review new purchase orders, send quotations, raise invoices, and stay ahead of buyer actions from one clear workspace."
        actions={<SupplierPortalPrimaryActions />}
      />

      {!error && (
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <SupplierPortalKpiCard
            label="Total orders"
            value={isLoading ? "..." : totalPos}
            helper="All purchase orders shared with this supplier login."
            icon={ClipboardClock}
            tone="blue"
          />
          <SupplierPortalKpiCard
            label="Active orders"
            value={isLoading ? "..." : activePos}
            helper="Orders still moving through delivery or acknowledgement."
            icon={PackageCheck}
            tone="green"
          />
          <SupplierPortalKpiCard
            label="Awaiting response"
            value={isLoading ? "..." : awaitingAcknowledgement}
            helper="POs waiting for acknowledgement from your side."
            icon={FileSpreadsheet}
            tone={awaitingAcknowledgement > 0 ? "amber" : "blue"}
          />
          <SupplierPortalKpiCard
            label="Open balance"
            value={isLoading ? "..." : formatCurrency(outstandingValue || totalOrderValue)}
            helper="Outstanding value visible in invoices and payment follow-up."
            icon={HandCoins}
            tone="slate"
          />
        </section>
      )}

      {!error && (
        <div className="erp-portal-section overflow-hidden p-3 sm:p-4">
          <SupplierPortalTabs counts={tabCounts} />
        </div>
      )}

      {!error && (
        <div className="space-y-3">
          {awaitingAcknowledgement > 0 && (
            <SupplierPortalAlertBanner
              tone="warning"
              title={`${awaitingAcknowledgement} purchase order${awaitingAcknowledgement > 1 ? "s" : ""} need your response`}
              description="Open pending orders, acknowledge them quickly, and keep the buyer updated."
            />
          )}
          {overdueInvoices > 0 && (
            <SupplierPortalAlertBanner
              tone="critical"
              title={`${overdueInvoices} invoice${overdueInvoices > 1 ? "s are" : " is"} overdue`}
              description="Review invoice ageing and follow up with the buyer on delayed payments."
            />
          )}
        </div>
      )}

      {recentActionCards.length > 0 && !error && (
        <section className="grid gap-4 lg:grid-cols-3">
          {recentActionCards.map((item) => (
            <Link key={item.type} to={item.href} className="erp-portal-section transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md">
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-2">
                  <p className="text-sm font-medium text-slate-600">{item.label}</p>
                  <p className="text-3xl font-semibold tracking-tight text-slate-950">
                    {item.type === "invoice_payment" ? formatCurrency(item.count) : item.count}
                  </p>
                  <p className="text-sm text-slate-500">Review and act from the linked workspace.</p>
                </div>
                <div className="rounded-2xl bg-slate-100 p-3 text-slate-500">
                  <PackageCheck className="h-5 w-5" />
                </div>
              </div>
            </Link>
          ))}
        </section>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertDescription>
            <strong>Error:</strong> {error}
            <p className="mt-2 text-xs">Contact your system administrator to link your account to a supplier.</p>
          </AlertDescription>
        </Alert>
      )}

      {isLoading && !error && (
        <Alert>
          <AlertDescription>Loading your purchase orders and supplier actions...</AlertDescription>
        </Alert>
      )}

      {!error && (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.9fr)]">
          <section id="supplier-purchase-orders" className="erp-portal-section space-y-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div className="space-y-1">
                <h2 className="text-xl font-semibold text-slate-950">Your purchase orders</h2>
                <p className="text-sm text-slate-600">Open an order, acknowledge it, and send shipment notices when dispatch is ready.</p>
              </div>
              <Button asChild variant="outline" className="w-full sm:w-auto">
                <Link to="/supplier-portal/receipts">View shipment notices</Link>
              </Button>
            </div>

            <ResponsiveDataList
              data={rows}
              getRowKey={(item) => item.id}
              emptyState={
                <SupplierPortalEmptyState
                  title="No purchase orders yet"
                  description="Once the buyer assigns purchase orders to your supplier account, they will appear here."
                  actionHref="/supplier-portal/profile"
                  actionLabel="Contact admin"
                />
              }
              columns={[
                {
                  key: "po",
                  header: "PO",
                  cell: (item) => (
                    <div>
                      <p className="font-mono text-sm font-semibold text-slate-900">{item.po_number}</p>
                      <p className="text-xs text-slate-500">Supplier action workspace</p>
                    </div>
                  ),
                },
                {
                  key: "status",
                  header: "Status",
                  cell: (item) => <SupplierPortalStatusBadge status={item.status} />,
                },
                {
                  key: "amount",
                  header: "Amount",
                  headerClassName: "text-right",
                  className: "text-right",
                  cell: (item) => <span className="font-semibold text-slate-900">{formatCurrency(item.total_amount)}</span>,
                },
                {
                  key: "actions",
                  header: "Action",
                  headerClassName: "text-right",
                  className: "text-right",
                  cell: (item) => (
                    <div className="flex justify-end gap-2">
                      {normalizeStatus(item.status) === "sent" && (
                        <Button size="sm" variant="secondary" onClick={() => ack(item.id)}>
                          Acknowledge
                        </Button>
                      )}
                      <Button size="sm" variant="outline" asChild>
                        <Link to={`/supplier-portal/po/${item.id}`}>Details</Link>
                      </Button>
                    </div>
                  ),
                },
              ]}
              renderMobileCard={(item) => (
                <article className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <p className="font-mono text-sm font-semibold text-slate-900">{item.po_number}</p>
                      <p className="text-sm text-slate-500">{formatCurrency(item.total_amount)}</p>
                    </div>
                    <SupplierPortalStatusBadge status={item.status} />
                  </div>
                  <div className="mt-4 grid gap-2">
                    {normalizeStatus(item.status) === "sent" && (
                      <Button size="sm" variant="secondary" className="w-full" onClick={() => ack(item.id)}>
                        Acknowledge
                      </Button>
                    )}
                    <Button size="sm" variant="outline" className="w-full" asChild>
                      <Link to={`/supplier-portal/po/${item.id}`}>View details</Link>
                    </Button>
                  </div>
                </article>
              )}
            />
          </section>

          <section className="erp-portal-section space-y-4">
            <div className="space-y-1">
              <h2 className="text-xl font-semibold text-slate-950">Submit quotation</h2>
              <p className="text-sm text-slate-600">Turn around price updates quickly and optionally link them to an open PO.</p>
            </div>

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
                  if (open) void loadMaterials()
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
                  {!isMaterialsLoading &&
                    materials.length > 0 &&
                    materials.map((m) => (
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

            <div className="grid gap-3 sm:grid-cols-2">
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

            <Button onClick={submitQuote} className="w-full sm:w-auto">
              Submit quotation
            </Button>
          </section>
        </div>
      )}
    </div>
  )
}
