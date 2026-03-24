import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

export type StatusType = 
  | "active" 
  | "inactive" 
  | "low-stock" 
  | "out-of-stock" 
  | "expired" 
  | "pending" 
  | "completed"

interface StatusBadgeProps {
  status: StatusType
  label?: string
  className?: string
}

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  const getStatusStyles = () => {
    switch (status) {
      case "active":
      case "completed":
        return "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-500/25 border-emerald-500/20"
      case "inactive":
        return "bg-slate-500/15 text-slate-700 dark:text-slate-400 hover:bg-slate-500/25 border-slate-500/20"
      case "pending":
      case "low-stock":
        return "bg-amber-500/15 text-amber-700 dark:text-amber-400 hover:bg-amber-500/25 border-amber-500/20"
      case "out-of-stock":
      case "expired":
        return "bg-destructive/15 text-destructive dark:text-destructive-foreground hover:bg-destructive/25 border-destructive/20"
      default:
        return "bg-primary/15 text-primary"
    }
  }

  const defaultLabel = status.split("-").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ")

  return (
    <Badge 
      variant="outline" 
      className={cn("font-medium transition-colors border", getStatusStyles(), className)}
    >
      {label || defaultLabel}
    </Badge>
  )
}
