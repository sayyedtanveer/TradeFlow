import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { AlertCircle, Check, Zap, Copy } from "lucide-react"
import { bomService } from "@/services/bom.service"
import { BOM } from "@/types/bom.types"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"

interface VersionSelectionPanelProps {
  productId: string
  isTemplate: boolean
  onCreateNew: () => void
  onOpenExisting: (bom: BOM) => void
  isCreatingNew: boolean
}

export function VersionSelectionPanel({
  productId,
  isTemplate,
  onCreateNew,
  onOpenExisting,
  isCreatingNew,
}: VersionSelectionPanelProps) {
  const [selectedVersionId, setSelectedVersionId] = useState<string>("")

  // Fetch existing BOMs for this product
  const { 
    data: bomsData, 
    isLoading, 
    isError,
    refetch
  } = useQuery({
    queryKey: ["product-boms", productId, isTemplate],
    queryFn: () => bomService.getBOMsForProduct(productId, isTemplate),
    staleTime: 30_000,
  })

  const boms = bomsData?.items ?? []
  const activeBom = boms.find(b => b.is_active)
  const hasExistingBoms = boms.length > 0

  const handleSelectExisting = () => {
    const selected = boms.find(b => b.id === selectedVersionId)
    if (selected) {
      onOpenExisting(selected)
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-48 rounded-lg" />
      </div>
    )
  }

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="w-4 h-4" />
        <AlertDescription>
          Failed to load existing BOMs.{" "}
          <Button 
            variant="link" 
            className="h-auto p-0 text-sm" 
            onClick={() => refetch()}
          >
            Try again
          </Button>
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-6">
      {/* Active BOM Warning */}
      {activeBom && (
        <Alert className="border-amber-200 bg-amber-50">
          <Zap className="w-4 h-4 text-amber-600" />
          <AlertDescription className="text-amber-900">
            An active BOM ({activeBom.version}) already exists. Creating a new version will not affect the current one in production.
          </AlertDescription>
        </Alert>
      )}

      {/* No Existing BOMs */}
      {!hasExistingBoms && (
        <div className="p-6 border-2 border-dashed rounded-lg bg-muted/30">
          <p className="text-muted-foreground mb-4">
            No Bill of Materials exists for this product yet.
          </p>
          <Button 
            onClick={onCreateNew}
            disabled={isCreatingNew}
            size="lg"
          >
            Create First BOM
          </Button>
        </div>
      )}

      {/* Existing BOMs - Option 1: Create New Version */}
      {hasExistingBoms && (
        <div className="space-y-4">
          <div>
            <Label className="text-base">Create New Version</Label>
            <p className="text-sm text-muted-foreground mt-1">
              Start fresh with a new BOM version
            </p>
          </div>
          <Button 
            onClick={onCreateNew}
            disabled={isCreatingNew}
            variant="outline"
            size="lg"
            className="w-full"
          >
            <Copy className="w-4 h-4 mr-2" />
            Create New BOM Version
          </Button>
        </div>
      )}

      {/* Existing BOMs - Option 2: Open Existing */}
      {hasExistingBoms && (
        <div className="space-y-4">
          <div>
            <Label className="text-base">Or Open Existing Version</Label>
            <p className="text-sm text-muted-foreground mt-1">
              Continue editing an existing BOM version
            </p>
          </div>
          <div className="border rounded-lg bg-card overflow-hidden">
            <div className="max-h-60 overflow-y-auto">
              {boms.map((bom) => (
                <button
                  key={bom.id}
                  onClick={() => setSelectedVersionId(bom.id)}
                  className={`w-full px-4 py-3 text-left border-b last:border-b-0 transition-colors ${
                    selectedVersionId === bom.id
                      ? "bg-primary/5 border-primary"
                      : "hover:bg-muted/50"
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono font-semibold">{bom.version}</span>
                        {bom.is_active && (
                          <Badge variant="default" className="text-xs">
                            <Check className="w-3 h-3 mr-1" />
                            Active
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {bom.valid_from ? new Date(bom.valid_from).toLocaleDateString() : "No date"}
                        {bom.valid_to && ` - ${new Date(bom.valid_to).toLocaleDateString()}`}
                      </p>
                    </div>
                    <div className={`w-5 h-5 rounded border-2 flex-shrink-0 transition-all ${
                      selectedVersionId === bom.id
                        ? "bg-primary border-primary"
                        : "border-muted-foreground"
                    }`} />
                  </div>
                </button>
              ))}
            </div>
          </div>
          <Button 
            onClick={handleSelectExisting}
            disabled={!selectedVersionId || isCreatingNew}
            size="lg"
            className="w-full"
          >
            Open Selected Version
          </Button>
        </div>
      )}
    </div>
  )
}
