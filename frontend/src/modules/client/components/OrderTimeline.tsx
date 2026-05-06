import { cn } from "@/lib/utils"
import type { ClientTimelineStep } from "../services/client.service"

interface OrderTimelineProps {
  steps: ClientTimelineStep[]
}

const toneMap: Record<ClientTimelineStep["status"], string> = {
  completed: "bg-emerald-500 text-emerald-700 border-emerald-500",
  current: "bg-cyan-500 text-cyan-700 border-cyan-500",
  upcoming: "bg-slate-200 text-slate-500 border-slate-300",
  cancelled: "bg-rose-500 text-rose-700 border-rose-500",
}

export default function OrderTimeline({ steps }: OrderTimelineProps) {
  return (
    <div className="overflow-x-auto">
      <div className="flex min-w-[540px] items-start gap-3 sm:min-w-[640px]">
        {steps.map((step, index) => (
          <div key={`${step.label}-${index}`} className="flex flex-1 items-center gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-3">
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-full border text-xs font-semibold uppercase tracking-wide",
                    toneMap[step.status]
                  )}
                >
                  {index + 1}
                </div>
                {index < steps.length - 1 && (
                  <div
                    className={cn(
                      "h-1 flex-1 rounded-full",
                      step.status === "completed" || step.status === "current" ? "bg-cyan-400" : "bg-slate-200"
                    )}
                  />
                )}
              </div>
              <div className="mt-2">
                <p className="text-sm font-medium">{step.label}</p>
                <p className="text-xs uppercase tracking-[0.15em] text-muted-foreground">{step.status}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
