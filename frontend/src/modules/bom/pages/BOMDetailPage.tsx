import { useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import {
  ArrowLeft, GitBranch, Package2, Zap, Lock, AlertCircle
} from "lucide-react"
import { bomService } from "@/services/bom.service"
import { BOM } from "@/types/bom.types"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Separator } from "@/components/ui/separator"
import { usePermissions } from "@/hooks/usePermissions"
import { BOMTreeView } from "../components/BOMTreeView"
import { BOMVersionPanel } from "../components/BOMVersionPanel"
import { BOMCostBreakdown } from "../components/BOMCostBreakdown"
import { BOMOperationList } from "../components/BOMOperationList"
import { BOMActivateDialog } from "../components/BOMActivateDialog"
import { BOMCopyDialog } from "../components/BOMCopyDialog"
import { toast } from "sonner"

export default function BOMDetailPage() {
  const { bomId } = useParams<{ bomId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { canEditBOM } = usePermissions()

  const [activateOpen, setActivateOpen] = useState(false)
  const [copyOpen, setCopyOpen] = useState(false)
  const [activeTab, setActiveTab] = useState("tree")

  const { data: bom, isLoading, isError, error } = useQuery({
    queryKey: ["bom", bomId],
    queryFn: () => bomService.getBOM(bomId!),
    enabled: !!bomId,
    staleTime: 30_000,
  })

  // Fetch product context for version panel
  const productId = bom?.variant_id ?? bom?.template_id
  const isTemplate = !bom?.variant_id

  if (isLoading) {
    return (
      <div className="w-full space-y-6">
        <div className="flex items-center gap-3">
          <Skeleton className="h-9 w-9 rounded-md" />
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-6 w-20" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <Skeleton className="h-64 rounded-xl" />
          <Skeleton className="col-span-3 h-96 rounded-xl" />
        </div>
      </div>
    )
  }

  if (isError || !bom) {
    return (
      <div className="p-8 flex flex-col items-center gap-4">
        <Alert variant="destructive" className="max-w-md">
          <AlertCircle className="w-4 h-4" />
          <AlertDescription>
            {(error as any)?.response?.data?.detail || "BOM not found."}
          </AlertDescription>
        </Alert>
        <Button variant="outline" onClick={() => navigate("/bom/list")}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to BOM List
        </Button>
      </div>
    )
  }

  const onActivated = (updated: BOM) => {
    qc.setQueryData(["bom", bomId], updated)
    qc.invalidateQueries({ queryKey: ["bom-versions"] })
    toast.success(`BOM v${updated.version} activated`)
  }

  const onCopied = (newBom: BOM) => {
    qc.invalidateQueries({ queryKey: ["bom-versions"] })
    navigate(`/bom/${newBom.id}`)
  }

  return (
    <div className="w-full space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate("/bom/list")}
          className="-ml-2 self-start"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          BOMs
        </Button>
        <Separator orientation="vertical" className="h-6 hidden sm:block" />
        <div className="flex flex-1 items-center gap-3 min-w-0 flex-wrap">
          <h1 className="text-xl font-semibold truncate">
            BOM v{bom.version}
          </h1>
          <Badge
            className={
              bom.is_active
                ? "bg-green-50 text-green-700 border-green-200"
                : "text-muted-foreground border"
            }
          >
            {bom.is_active ? (
              <>
                <Zap className="w-3 h-3 mr-1" />
                Active
              </>
            ) : (
              "Draft"
            )}
          </Badge>
          {!canEditBOM() && (
            <Badge variant="outline" className="text-muted-foreground text-xs">
              <Lock className="w-3 h-3 mr-1" />
              Read-only
            </Badge>
          )}
        </div>

        {/* Action buttons */}
        {canEditBOM() && (
          <div className="flex gap-2 flex-shrink-0">
            {!bom.is_active && (
              <Button
                size="sm"
                onClick={() => setActivateOpen(true)}
                className="bg-green-600 hover:bg-green-700"
              >
                <Zap className="w-3.5 h-3.5 mr-1.5" />
                Activate
              </Button>
            )}
            <Button
              size="sm"
              variant="outline"
              onClick={() => setCopyOpen(true)}
            >
              <GitBranch className="w-3.5 h-3.5 mr-1.5" />
              Copy
            </Button>
          </div>
        )}
      </div>

      {/* Meta info row */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
        {bom.valid_from && (
          <span>
            Valid from: <strong className="text-foreground">
              {new Date(bom.valid_from).toLocaleDateString()}
            </strong>
          </span>
        )}
        {bom.valid_to && (
          <span>
            to <strong className="text-foreground">
              {new Date(bom.valid_to).toLocaleDateString()}
            </strong>
          </span>
        )}
        <span>
          Components: <strong className="text-foreground">{bom.lines.length}</strong>
        </span>
      </div>

      {/* Main two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
        {/* Left: Version panel */}
        {productId && (
          <div className="lg:col-span-1">
            <div className="rounded-xl border bg-card p-4">
              <BOMVersionPanel
                productId={productId}
                isTemplate={isTemplate}
                productName={`Product ${productId.slice(0, 8)}`}
                productCode={productId.slice(0, 8)}
                selectedBomId={bom.id}
                activeBomId={bom.is_active ? bom.id : undefined}
                onSelectBom={(b) => navigate(`/bom/${b.id}`)}
              />
            </div>
          </div>
        )}

        {/* Right: Tabs */}
        <div className={productId ? "lg:col-span-3" : "lg:col-span-4"}>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="w-full sm:w-auto">
              <TabsTrigger value="tree">
                <Package2 className="w-3.5 h-3.5 mr-1.5" />
                BOM Tree
              </TabsTrigger>
              <TabsTrigger value="operations">Operations</TabsTrigger>
              <TabsTrigger value="cost">Cost Breakdown</TabsTrigger>
            </TabsList>

            {/* BOM Tree tab */}
            <TabsContent value="tree" className="mt-4">
              <div className="rounded-xl border bg-card p-4">
                {bom.lines.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 gap-3 text-muted-foreground">
                    <Package2 className="w-10 h-10" />
                    <p className="text-sm">This BOM has no components yet.</p>
                    {canEditBOM() && !bom.is_active && (
                      <p className="text-xs">Edit the BOM to add components.</p>
                    )}
                  </div>
                ) : (
                  <BOMTreeView bomId={bom.id} />
                )}
              </div>
            </TabsContent>

            {/* Operations tab */}
            <TabsContent value="operations" className="mt-4">
              <div className="rounded-xl border bg-card p-4">
                <BOMOperationList bom={bom} canEdit={canEditBOM() && !bom.is_active} />
              </div>
            </TabsContent>

            {/* Cost tab */}
            <TabsContent value="cost" className="mt-4">
              <div className="rounded-xl border bg-card p-4">
                <BOMCostBreakdown bom={bom} />
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Dialogs */}
      <BOMActivateDialog
        open={activateOpen}
        bom={bom}
        onClose={() => setActivateOpen(false)}
        onActivated={onActivated}
      />
      <BOMCopyDialog
        open={copyOpen}
        bom={bom}
        productId={productId ?? ""}
        onClose={() => setCopyOpen(false)}
        onCopied={onCopied}
      />
    </div>
  )
}
