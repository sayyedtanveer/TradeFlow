import { Handle, Position, NodeProps, type Node } from "@xyflow/react"
import { 
  Box, 
  Users, 
  Package, 
  PackageSearch, 
  Layers, 
  Factory, 
  CircleCheck,
  Building,
  ClipboardList,
  LucideIcon 
} from "lucide-react"
import { cn } from "@/lib/utils"
import { SystemModule } from "@/services/system-map.service"

// Pre-register known icons that backend might send
const iconMap: Record<string, LucideIcon> = {
  Box,
  Users,
  Package,
  PackageSearch,
  Layers,
  Factory,
  Building,
  ClipboardList
}

export type SystemModuleNodeData = SystemModule & {
  isCurrent?: boolean
  [key: string]: unknown
}

export function SystemModuleNode({ data, selected }: NodeProps<Node<SystemModuleNodeData, "systemModule">>) {
  const IconComponent = iconMap[data.icon as string] || Box
  
  return (
    <div
      className={cn(
        "px-4 py-3 shadow-md rounded-xl bg-card border-2 transition-all min-w-[200px]",
        selected ? "border-primary ring-2 ring-primary/20" : "border-border",
        data.isCurrent && "bg-primary/5 border-primary shadow-primary/20"
      )}
    >
      <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-muted-foreground" />
      
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <div className={cn(
            "p-2 rounded-lg",
            data.isCurrent ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"
          )}>
            <IconComponent className="w-5 h-5" />
          </div>
          <div>
            <div className="font-semibold text-sm">{data.name}</div>
            <div className="text-xs text-muted-foreground font-mono">{data.id}</div>
          </div>
        </div>

        <div className="flex items-center justify-between mt-1">
          <span className="text-[10px] uppercase font-semibold text-muted-foreground tracking-wider">
            {data.route}
          </span>
          {data.status === "active" && (
            <div className="flex items-center gap-1 text-[10px] font-medium text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded-sm border border-emerald-100">
              <CircleCheck className="w-3 h-3" />
              Active
            </div>
          )}
        </div>
      </div>

      <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-primary" />
    </div>
  )
}
