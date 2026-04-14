import { useEffect, useState } from "react"
import { supplyChainApi, type SupplierPerformance } from "@/services/supply-chain.service"
import { useToast } from "@/hooks/use-toast"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Progress } from "@/components/ui/progress"
import { TrendingUp, Clock, CheckSquare, Star, BarChart3 } from "lucide-react"

function MetricCard({
  icon,
  label,
  value,
  suffix = "%",
  color = "text-foreground",
}: {
  icon: React.ReactNode
  label: string
  value?: number | null
  suffix?: string
  color?: string
}) {
  return (
    <div className="flex items-center gap-3">
      <div className="p-2 rounded-lg bg-muted">{icon}</div>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className={`text-lg font-bold ${color}`}>
          {value != null ? `${value}${suffix}` : "N/A"}
        </p>
      </div>
    </div>
  )
}

function scoreColor(v?: number | null) {
  if (v == null) return "text-muted-foreground"
  if (v >= 90) return "text-emerald-600"
  if (v >= 70) return "text-amber-600"
  return "text-red-500"
}

export default function SupplierPerformancePage() {
  const { toast } = useToast()
  const [data, setData] = useState<SupplierPerformance[]>([])
  const [selected, setSelected] = useState<SupplierPerformance | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supplyChainApi
      .listSupplierPerformance()
      .then((r) => {
        setData(r.data)
        if (r.data.length > 0) setSelected(r.data[0])
      })
      .catch(() => toast({ title: "Failed to load performance data", variant: "destructive" }))
      .finally(() => setLoading(false))
  }, [toast])

  if (loading)
    return <div className="p-8 text-center text-muted-foreground text-sm">Loading metrics…</div>

  return (
    <div className="space-y-6 p-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <BarChart3 className="h-6 w-6" /> Supplier Performance Dashboard
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          On-time delivery, quality acceptance, and lead time metrics across all active suppliers.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ── Supplier list ── */}
        <div className="lg:col-span-1 space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Suppliers ({data.length})
          </h2>
          {data.length === 0 && (
            <p className="text-sm text-muted-foreground">No active suppliers with data.</p>
          )}
          {data.map((s) => (
            <button
              key={s.supplier_id}
              id={`perf-supplier-${s.supplier_id.slice(0, 8)}`}
              onClick={() => setSelected(s)}
              className={`w-full text-left rounded-lg border p-3 transition-colors hover:bg-accent ${
                selected?.supplier_id === s.supplier_id ? "border-primary bg-primary/5" : ""
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-sm">{s.supplier_name}</p>
                  <p className="text-xs text-muted-foreground">{s.supplier_code}</p>
                </div>
                <div className="text-right">
                  {s.on_time_delivery_pct != null && (
                    <span className={`text-sm font-bold ${scoreColor(s.on_time_delivery_pct)}`}>
                      {s.on_time_delivery_pct}%
                    </span>
                  )}
                  <p className="text-xs text-muted-foreground">on-time</p>
                </div>
              </div>
              {s.on_time_delivery_pct != null && (
                <Progress value={s.on_time_delivery_pct} className="h-1 mt-2" />
              )}
            </button>
          ))}
        </div>

        {/* ── Detail panel ── */}
        <div className="lg:col-span-2 space-y-4">
          {!selected ? (
            <div className="p-8 text-center text-muted-foreground rounded-lg border">
              Select a supplier to view details.
            </div>
          ) : (
            <>
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>{selected.supplier_name}</CardTitle>
                      <CardDescription className="font-mono">{selected.supplier_code}</CardDescription>
                    </div>
                    {selected.performance_rating != null && (
                      <div className="flex items-center gap-1 text-amber-500">
                        <Star className="h-5 w-5 fill-current" />
                        <span className="text-lg font-bold">{selected.performance_rating}</span>
                        <span className="text-xs text-muted-foreground">/5</span>
                      </div>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                    <MetricCard
                      icon={<Clock className="h-4 w-4 text-blue-500" />}
                      label="On-Time Delivery"
                      value={selected.on_time_delivery_pct}
                      color={scoreColor(selected.on_time_delivery_pct)}
                    />
                    <MetricCard
                      icon={<CheckSquare className="h-4 w-4 text-emerald-500" />}
                      label="Quality Acceptance"
                      value={selected.quality_acceptance_pct}
                      color={scoreColor(selected.quality_acceptance_pct)}
                    />
                    <MetricCard
                      icon={<TrendingUp className="h-4 w-4 text-violet-500" />}
                      label="Avg Lead Time"
                      value={selected.avg_lead_time_days}
                      suffix=" days"
                      color="text-foreground"
                    />
                  </div>

                  {/* Visual progress bars */}
                  <div className="mt-6 space-y-3">
                    {[
                      { label: "On-Time Delivery", value: selected.on_time_delivery_pct },
                      { label: "Quality Acceptance", value: selected.quality_acceptance_pct },
                    ].map(({ label, value }) => (
                      <div key={label}>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-muted-foreground">{label}</span>
                          <span className={scoreColor(value)}>
                            {value != null ? `${value}%` : "No data"}
                          </span>
                        </div>
                        <div className="h-2 rounded-full bg-muted overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${
                              value == null
                                ? ""
                                : value >= 90
                                ? "bg-emerald-500"
                                : value >= 70
                                ? "bg-amber-400"
                                : "bg-red-500"
                            }`}
                            style={{ width: `${value ?? 0}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Price history */}
              {selected.price_history.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Recent Price History</CardTitle>
                    <CardDescription>Last unit prices recorded during GRN receipt.</CardDescription>
                  </CardHeader>
                  <CardContent className="p-0">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Material</TableHead>
                          <TableHead className="text-right">Unit Price</TableHead>
                          <TableHead>Date</TableHead>
                          <TableHead>Trend</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {selected.price_history.map((p, i) => {
                          const prev = selected.price_history[i + 1]
                          const trend =
                            prev == null
                              ? null
                              : p.unit_price < prev.unit_price
                              ? "down"
                              : p.unit_price > prev.unit_price
                              ? "up"
                              : "flat"
                          return (
                            <TableRow key={`${p.material_id}-${p.effective_from}`}>
                              <TableCell>
                                <p className="font-medium text-sm">{p.material_code}</p>
                                <p className="text-xs text-muted-foreground">{p.material_name}</p>
                              </TableCell>
                              <TableCell className="text-right font-mono">
                                ₹ {p.unit_price.toFixed(4)}
                              </TableCell>
                              <TableCell className="text-sm text-muted-foreground">
                                {p.effective_from ?? "—"}
                              </TableCell>
                              <TableCell>
                                {trend === "down" && (
                                  <Badge variant="secondary" className="text-emerald-600 text-xs">
                                    ↓ Lower
                                  </Badge>
                                )}
                                {trend === "up" && (
                                  <Badge variant="destructive" className="text-xs">
                                    ↑ Higher
                                  </Badge>
                                )}
                                {trend === "flat" && (
                                  <Badge variant="outline" className="text-xs">
                                    → Same
                                  </Badge>
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
            </>
          )}
        </div>
      </div>
    </div>
  )
}
