import { useState, useCallback } from "react"
import { useQuery } from "@tanstack/react-query"
import { ChevronRight, ChevronDown, Package2, Layers, Box, Loader2, AlertCircle } from "lucide-react"
import { bomService } from "@/services/bom.service"
import { BOMTreeNode } from "@/types/bom.types"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"

interface BOMTreeViewProps {
  bomId: string
}

// ─── Type badge & icon ────────────────────────────────────────────────────────

const typeConfig = {
  material: {
    label: "Material",
    icon: Package2,
    badgeClass: "bg-amber-100 text-amber-800 border-amber-200",
  },
  template: {
    label: "Template",
    icon: Layers,
    badgeClass: "bg-blue-100 text-blue-800 border-blue-200",
  },
  variant: {
    label: "Variant",
    icon: Box,
    badgeClass: "bg-violet-100 text-violet-800 border-violet-200",
  },
} as const

// ─── Single node ──────────────────────────────────────────────────────────────

function TreeNode({
  node,
  depth,
  maxDepth,
}: {
  node: BOMTreeNode
  depth: number
  maxDepth: number
}) {
  const [expanded, setExpanded] = useState(depth === 0)
  const hasChildren = node.children && node.children.length > 0
  const cfg = typeConfig[node.type] ?? typeConfig.material
  const Icon = cfg.icon

  const indent = depth * 20

  return (
    <div className="select-none">
      <div
        className={cn(
          "flex items-center gap-2 py-2 px-3 rounded-md transition-colors cursor-pointer group",
          "hover:bg-accent/60",
          depth === 0 && "bg-accent/30 font-medium"
        )}
        style={{ paddingLeft: `${12 + indent}px` }}
        onClick={() => hasChildren && setExpanded((v) => !v)}
      >
        {/* Expand toggle */}
        <span className="w-4 h-4 flex items-center justify-center flex-shrink-0 text-muted-foreground">
          {hasChildren ? (
            expanded ? (
              <ChevronDown className="w-3.5 h-3.5" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5" />
            )
          ) : (
            <span className="w-3.5 h-3.5 border-l border-b border-border ml-1" />
          )}
        </span>

        {/* Icon */}
        <Icon className="w-4 h-4 text-muted-foreground flex-shrink-0" />

        {/* Name */}
        <span className="flex-1 text-sm truncate">{node.name}</span>
        {node.code && (
          <span className="text-xs text-muted-foreground font-mono hidden sm:inline">
            {node.code}
          </span>
        )}

        {/* Qty */}
        <span className="text-sm tabular-nums text-foreground ml-2 flex-shrink-0">
          {node.quantity}
          {node.unit && (
            <span className="text-muted-foreground ml-1 text-xs">{node.unit}</span>
          )}
        </span>

        {/* Scrap */}
        {node.scrap_percentage != null && node.scrap_percentage > 0 && (
          <span className="text-xs text-amber-600 flex-shrink-0 hidden md:inline">
            +{node.scrap_percentage}% scrap
          </span>
        )}

        {/* Type badge */}
        <Badge
          variant="outline"
          className={cn("text-xs flex-shrink-0 capitalize hidden sm:inline-flex", cfg.badgeClass)}
        >
          {cfg.label}
        </Badge>

        {/* Cost */}
        {node.cost != null && (
          <span className="text-xs font-medium text-green-700 flex-shrink-0">
            ${node.cost.toFixed(2)}
          </span>
        )}
      </div>

      {/* Depth limit warning */}
      {depth >= maxDepth && hasChildren && (
        <div
          className="flex items-center gap-1 text-xs text-amber-600 py-1"
          style={{ paddingLeft: `${12 + indent + 24}px` }}
        >
          <AlertCircle className="w-3 h-3" />
          Max depth reached
        </div>
      )}

      {/* Children */}
      {expanded && hasChildren && depth < maxDepth && (
        <div className="relative">
          {/* Vertical connector line */}
          <div
            className="absolute top-0 bottom-2 border-l border-dashed border-border"
            style={{ left: `${16 + indent + 20}px` }}
          />
          {node.children.map((child, i) => (
            <TreeNode key={child.id + i} node={child} depth={depth + 1} maxDepth={maxDepth} />
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Root component ───────────────────────────────────────────────────────────

export function BOMTreeView({ bomId }: BOMTreeViewProps) {
  const MAX_DEPTH = 20
  const [maxDepth, setMaxDepth] = useState(5)

  const { data: tree, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["bom-tree", bomId, maxDepth],
    queryFn: () => bomService.getBOMTree(bomId, maxDepth),
    staleTime: 30_000,
    retry: 1,
  })

  const expandMore = useCallback(() => {
    setMaxDepth((d) => Math.min(d + 5, MAX_DEPTH))
  }, [])

  if (isLoading) {
    return (
      <div className="space-y-2 p-4">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-9 w-full rounded-md" style={{ marginLeft: `${i * 16}px`, width: `calc(100% - ${i * 16}px)` }} />
        ))}
      </div>
    )
  }

  if (isError || !tree) {
    return (
      <div className="flex flex-col items-center justify-center p-10 gap-3 text-muted-foreground">
        <AlertCircle className="w-8 h-8 text-destructive/60" />
        <p className="text-sm">Failed to load BOM tree.</p>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          Retry
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {/* Controls row */}
      <div className="flex items-center justify-between px-3 pb-2 border-b">
        <span className="text-xs text-muted-foreground">
          Showing up to depth {maxDepth}
        </span>
        <div className="flex items-center gap-2">
          {isFetching && <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />}
          {maxDepth < MAX_DEPTH && (
            <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={expandMore}>
              Load deeper levels
            </Button>
          )}
        </div>
      </div>

      {/* Tree */}
      <TreeNode node={tree} depth={0} maxDepth={maxDepth} />
    </div>
  )
}
