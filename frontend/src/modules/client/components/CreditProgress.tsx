import { cn } from "@/lib/utils"

interface CreditProgressProps {
  limit: number | null
  used: number
  remaining: number | null
  usagePercent: number | null
  compact?: boolean
}

export default function CreditProgress({
  limit,
  used,
  remaining,
  usagePercent,
  compact = false,
}: CreditProgressProps) {
  const tone =
    usagePercent === null ? "bg-slate-500" : usagePercent >= 100 ? "bg-red-500" : usagePercent >= 80 ? "bg-amber-500" : "bg-emerald-500"

  return (
    <div className="space-y-3">
      <div className={cn("flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between", compact && "text-sm")}>
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Credit Used</p>
          <p className="text-2xl font-semibold">{used.toFixed(2)}</p>
        </div>
        <div className="sm:text-right">
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Remaining</p>
          <p className="text-lg font-medium">{remaining === null ? "Unlimited" : remaining.toFixed(2)}</p>
        </div>
      </div>
      <div className="space-y-2">
        <div className="h-3 overflow-hidden rounded-full bg-slate-200">
          <div
            className={cn("h-full rounded-full transition-all", tone)}
            style={{ width: `${Math.max(0, Math.min(100, usagePercent ?? 0))}%` }}
          />
        </div>
        <div className="flex flex-col gap-1 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <span>{limit === null ? "No credit ceiling" : `Limit ${limit.toFixed(2)}`}</span>
          <span>{usagePercent === null ? "N/A" : `${usagePercent.toFixed(1)}% used`}</span>
        </div>
      </div>
    </div>
  )
}
