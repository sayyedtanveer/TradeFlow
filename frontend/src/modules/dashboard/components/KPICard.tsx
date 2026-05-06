import { Link } from "react-router-dom"
import { KPIData } from "@/types/inventory.types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ArrowDownIcon, ArrowRightIcon, ArrowUpIcon, PackageOpen } from "lucide-react"
import { cn } from "@/lib/utils"

interface KPICardProps {
  data: KPIData
  href?: string
  tone?: "primary" | "secondary" | "soft" | "glass"
}

export function KPICard({ data, href, tone = "primary" }: KPICardProps) {
  const toneClass =
    tone === "secondary"
      ? "erp-kpi-gradient-alt"
      : tone === "soft"
        ? "erp-kpi-gradient-soft"
        : tone === "glass"
          ? "border border-slate-200/80 bg-white text-slate-900"
          : "erp-kpi-gradient"

  const content = (
    <Card className={cn("overflow-hidden", toneClass, href && "cursor-pointer hover:border-primary/40")}>
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3">
        <CardTitle className={cn("text-[11px] font-semibold uppercase tracking-[0.24em]", tone === "glass" ? "text-slate-600" : "text-white/72")}>
          {data.label}
        </CardTitle>
        <div className={cn("rounded-2xl border p-2.5 shadow-sm", tone === "glass" ? "border-blue-100 bg-blue-50 text-blue-600" : "border-white/10 bg-white/12 text-white")}>
          <PackageOpen className="h-4 w-4" />
        </div>
      </CardHeader>
      <CardContent>
        <div className={cn("text-3xl font-semibold leading-none sm:text-[2rem]", tone === "glass" ? "text-slate-900" : "text-white")}>
          {data.value}
        </div>
        <p className={cn("mt-4 flex items-center text-xs", tone === "glass" ? "text-slate-500" : "text-white/75")}>
          {data.trend === "up" && <ArrowUpIcon className={cn("mr-1 h-3 w-3", tone === "glass" ? "text-emerald-500" : "text-emerald-200")} />}
          {data.trend === "down" && <ArrowDownIcon className={cn("mr-1 h-3 w-3", tone === "glass" ? "text-red-500" : "text-rose-200")} />}
          {data.trend === "neutral" && <ArrowRightIcon className={cn("mr-1 h-3 w-3", tone === "glass" ? "text-slate-400" : "text-white/60")} />}
          <span
            className={
              data.trend === "down" && data.label.includes("Alerts")
                ? tone === "glass"
                  ? "font-medium text-red-600"
                  : "font-medium text-rose-200"
                : data.trend === "up" && !data.label.includes("Alerts")
                  ? tone === "glass"
                    ? "font-medium text-emerald-600"
                    : "font-medium text-emerald-200"
                  : ""
            }
          >
            {data.change > 0 ? "+" : ""}{data.change}
          </span>
          <span className={cn("ml-1", tone === "glass" ? "text-slate-500" : "text-white/65")}>
            from last month
          </span>
        </p>
      </CardContent>
    </Card>
  )

  if (href) {
    return <Link to={href} className="block">{content}</Link>
  }

  return content
}
