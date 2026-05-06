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
        return "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
      case "inactive":
        return "border-slate-200 bg-slate-100 text-slate-600 hover:bg-slate-200"
      case "pending":
      case "low-stock":
        return "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100"
      case "out-of-stock":
      case "expired":
        return "border-red-200 bg-red-50 text-red-700 hover:bg-red-100"
      default:
        return "border-blue-200 bg-blue-50 text-blue-700"
    }
  }

  const defaultLabel = status.split("-").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ")

  return (
    <Badge 
      variant="outline" 
      className={cn("font-medium transition-colors", getStatusStyles(), className)}
    >
      {label || defaultLabel}
    </Badge>
  )
}
