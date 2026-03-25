import { useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import {
  CheckCircle2, Circle, Copy, Zap, CalendarDays, AlertCircle
} from "lucide-react"
import { bomService } from "@/services/bom.service"
import { BOM } from "@/types/bom.types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { BOMCopyDialog } from "./BOMCopyDialog"
import { BOMActivateDialog } from "./BOMActivateDialog"

interface BOMVersionPanelProps {
  productId: string
  isTemplate: boolean
  productName: string
  productCode?: string
  activeBomId: string | undefined
  selectedBomId: string
  onSelectBom: (bom: BOM) => void
}

export function BOMVersionPanel({
  productId,
  isTemplate,
  productName,
  productCode,
  selectedBomId,
  onSelectBom,
}: BOMVersionPanelProps) {
  const qc = useQueryClient()
  const [copyOpen, setCopyOpen] = useState(false)
  const [activateOpen, setActivateOpen] = useState(false)
  const [targetBom, setTargetBom] = useState<BOM | null>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ["bom-versions", productId, isTemplate],
    queryFn: () => bomService.getBOMsForProduct(productId, isTemplate),
    staleTime: 30_000,
  })

  const boms = data?.items ?? []

  const handleCopy = (bom: BOM) => {
    setTargetBom(bom)
    setCopyOpen(true)
  }

  const handleActivate = (bom: BOM) => {
    setTargetBom(bom)
    setActivateOpen(true)
  }

  const onActivated = (bom: BOM) => {
    qc.invalidateQueries({ queryKey: ["bom-versions", productId] })
    onSelectBom(bom)
  }

  const onCopied = (bom: BOM) => {
    qc.invalidateQueries({ queryKey: ["bom-versions", productId] })
    onSelectBom(bom)
  }

  return (
    <div className="flex flex-col gap-1 min-w-0">
      {/* Product context header */}
      <div className="mb-3 px-1">
        <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
          {isTemplate ? "Template" : "Variant"}
        </p>
        <h3 className="font-semibold text-base truncate">{productName}</h3>
        {productCode && (
          <p className="text-xs text-muted-foreground font-mono">{productCode}</p>
        )}
        <p className="text-xs text-muted-foreground mt-1">
          {boms.length} version{boms.length !== 1 ? "s" : ""}
        </p>
      </div>

      {/* Versions list */}
      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-16 w-full rounded-lg" />
          ))}
        </div>
      ) : isError ? (
        <div className="flex items-center gap-2 text-xs text-destructive p-3 bg-destructive/10 rounded-lg">
          <AlertCircle className="w-4 h-4" />
          Failed to load versions
        </div>
      ) : boms.length === 0 ? (
        <div className="text-xs text-muted-foreground text-center py-6 border border-dashed rounded-lg">
          No BOM versions yet
        </div>
      ) : (
        boms.map((bom) => {
          const isSelected = bom.id === selectedBomId
          const isActive = bom.is_active
          return (
            <div
              key={bom.id}
              onClick={() => onSelectBom(bom)}
              className={cn(
                "group rounded-lg border p-3 cursor-pointer transition-all",
                "hover:border-primary/50 hover:bg-accent/40",
                isSelected
                  ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                  : "border-border bg-background"
              )}
            >
              <div className="flex items-start justify-between gap-2 min-w-0">
                <div className="flex items-center gap-2 min-w-0">
                  {isActive ? (
                    <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                  ) : (
                    <Circle className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                  )}
                  <div className="min-w-0">
                    <span className="font-medium text-sm truncate block">
                      v{bom.version}
                    </span>
                    {bom.valid_from && (
                      <span className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                        <CalendarDays className="w-3 h-3" />
                        {new Date(bom.valid_from).toLocaleDateString()}
                        {bom.valid_to && ` → ${new Date(bom.valid_to).toLocaleDateString()}`}
                      </span>
                    )}
                  </div>
                </div>
                <Badge
                  variant="outline"
                  className={cn(
                    "text-xs flex-shrink-0",
                    isActive
                      ? "bg-green-50 text-green-700 border-green-200"
                      : "text-muted-foreground"
                  )}
                >
                  {isActive ? "Active" : "Draft"}
                </Badge>
              </div>

              {/* Lines count */}
              <p className="text-xs text-muted-foreground mt-1.5">
                {bom.lines.length} component{bom.lines.length !== 1 ? "s" : ""}
              </p>

              {/* Action buttons — visible on hover or when selected */}
              <div
                className={cn(
                  "flex gap-1 mt-2 transition-opacity",
                  isSelected ? "opacity-100" : "opacity-0 group-hover:opacity-100"
                )}
                onClick={(e) => e.stopPropagation()}
              >
                {!isActive && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs flex-1"
                    onClick={() => handleActivate(bom)}
                  >
                    <Zap className="w-3 h-3 mr-1" />
                    Activate
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs flex-1"
                  onClick={() => handleCopy(bom)}
                >
                  <Copy className="w-3 h-3 mr-1" />
                  Copy
                </Button>
              </div>
            </div>
          )
        })
      )}

      {/* Dialogs */}
      {targetBom && (
        <>
          <BOMActivateDialog
            open={activateOpen}
            bom={targetBom}
            onClose={() => setActivateOpen(false)}
            onActivated={onActivated}
          />
          <BOMCopyDialog
            open={copyOpen}
            bom={targetBom}
            productId={productId}
            onClose={() => setCopyOpen(false)}
            onCopied={onCopied}
          />
        </>
      )}
    </div>
  )
}
