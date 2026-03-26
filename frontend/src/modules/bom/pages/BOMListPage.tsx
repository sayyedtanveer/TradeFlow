import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import {
  Layers, Search, CheckCircle2, Circle, AlertCircle,
  Copy, Eye, DollarSign, Edit2, ChevronDown
} from "lucide-react"
import { bomService } from "@/services/bom.service"
import { BOM } from "@/types/bom.types"
import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { usePermissions } from "@/hooks/usePermissions"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

// We list BOMs by fetching templates first, then their BOMs
export default function BOMListPage() {
  const navigate = useNavigate()
  const { canEditBOM } = usePermissions()
  const [search, setSearch] = useState("")
  const [showOnlyWithBOM, setShowOnlyWithBOM] = useState(false)
  const [showOnlyActive, setShowOnlyActive] = useState(false)

  const { data: tplData, isLoading, isError, refetch } = useQuery({
    queryKey: ["bom-list-templates"],
    queryFn: () => bomService.getTemplates({ page_size: 100 }),
    staleTime: 30_000,
  })

  const templates = tplData?.items ?? []
  
  // Apply filters
  const filtered = templates
    .filter((template) => {
      if (search) {
        return (
          template.name.toLowerCase().includes(search.toLowerCase()) ||
          template.code.toLowerCase().includes(search.toLowerCase())
        )
      }
      return true
    })
    .filter((_template) => {
      // This will be enhanced in the grid rendering to check if template has BOMs
      return true
    })

  return (
    <div className="w-full space-y-6">
      <PageHeader
        title="Bill of Materials"
        description="Manage multi-level BOMs, versions, and manufacturing routing."
        action={
          canEditBOM() ? (
            <Button onClick={() => navigate("/bom/new")} className="gap-1.5">
              <Layers className="w-4 h-4" />
              New BOM
            </Button>
          ) : undefined
        }
      />

      {/* Search and filters */}
      <div className="space-y-3">
        <div className="relative max-w-sm">
          <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-muted-foreground" />
          <Input
            className="pl-8"
            placeholder="Search products..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* Filter buttons */}
        <div className="flex flex-wrap gap-2">
          <Button
            variant={showOnlyWithBOM ? "default" : "outline"}
            size="sm"
            onClick={() => setShowOnlyWithBOM(!showOnlyWithBOM)}
            className="gap-1.5"
          >
            <Circle className="w-3 h-3" />
            Has BOMs
          </Button>
          <Button
            variant={showOnlyActive ? "default" : "outline"}
            size="sm"
            onClick={() => setShowOnlyActive(!showOnlyActive)}
            className="gap-1.5"
          >
            <CheckCircle2 className="w-3 h-3" />
            Active Only
          </Button>
        </div>
      </div>

      {isError && (
        <Alert variant="destructive">
          <AlertCircle className="w-4 h-4" />
          <div className="flex items-center justify-between w-full">
            <AlertDescription>Failed to load product list.</AlertDescription>
            <Button
              variant="outline"
              size="sm"
              className="ml-4 h-8"
              onClick={() => refetch()}
            >
              Retry
            </Button>
          </div>
        </Alert>
      )}

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-4 border border-dashed rounded-xl bg-muted/20">
          <div className="rounded-full bg-muted p-4">
            <Layers className="w-8 h-8 text-muted-foreground" />
          </div>
          <div className="text-center space-y-1">
            <h3 className="font-semibold text-base">
              {search ? "No matching products found" : "No Bill of Materials yet"}
            </h3>
            <p className="text-sm text-muted-foreground max-w-xs">
              {search
                ? "Try a different search term."
                : "To create a BOM, first create a Product Template, then open a product to create its Bill of Materials."}
            </p>
          </div>
          {!search && (
            <div className="flex gap-3">
              <Button variant="outline" onClick={() => navigate("/products")}>
                Go to Products
              </Button>
              {canEditBOM() && (
                <Button onClick={() => navigate("/bom/new")}>
                  <Layers className="w-4 h-4 mr-2" />
                  New BOM
                </Button>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((tpl) => (
            <TemplateCard
              key={tpl.id}
              templateId={tpl.id}
              name={tpl.name}
              code={tpl.code}
              showOnlyWithBOM={showOnlyWithBOM}
              showOnlyActive={showOnlyActive}
              onClick={() =>
                navigate(`/bom/list?templateId=${tpl.id}`)
              }
              onSelectBom={(bom) => navigate(`/bom/${bom.id}`)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Template card with mini version list ────────────────────────────────────

function TemplateCard({
  templateId,
  name,
  code,
  showOnlyWithBOM,
  showOnlyActive,
  onClick,
  onSelectBom,
}: {
  templateId: string
  name: string
  code: string
  showOnlyWithBOM: boolean
  showOnlyActive: boolean
  onClick: () => void
  onSelectBom: (bom: BOM) => void
}) {
  const navigate = useNavigate()
  const { canEditBOM } = usePermissions()
  const { data, isLoading } = useQuery({
    queryKey: ["bom-versions", templateId, true],
    queryFn: () => bomService.getBOMsForProduct(templateId, true),
    staleTime: 30_000,
  })

  const boms = data?.items ?? []
  const activeBom = boms.find((b) => b.is_active)

  // MUST call hooks before any conditional returns
  const { data: costData, isLoading: costLoading } = useQuery({
    queryKey: ["bom-cost", activeBom?.id],
    queryFn: () => bomService.getBOMCost(activeBom!.id),
    staleTime: 30_000,
    enabled: !!activeBom,
  })

  // Apply filters AFTER all hooks are called
  const hasBoMs = boms.length > 0
  if (showOnlyWithBOM && !hasBoMs) return null
  if (showOnlyActive && !activeBom) return null

  const componentCount = activeBom?.lines?.length ?? 0
  const totalCost = costData?.total_cost ?? 0
  const currency = costData?.currency ?? "USD"

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (activeBom) {
      navigate(`/bom/${activeBom.id}`)
    }
  }

  const handleViewTree = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (activeBom) {
      navigate(`/bom/${activeBom.id}?tab=tree`)
    }
  }

  const handleViewCost = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (activeBom) {
      navigate(`/bom/${activeBom.id}?tab=costs`)
    }
  }

  return (
    <Card
      className="cursor-pointer hover:border-primary/50 hover:bg-accent/20 transition-all group"
      onClick={onClick}
    >
      <CardContent className="p-4 space-y-3">
        {/* Header with quick actions */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <h3 className="font-semibold text-sm truncate">{name}</h3>
            <p className="text-xs text-muted-foreground font-mono">{code}</p>
          </div>
          
          {/* Quick action menu */}
          {activeBom && canEditBOM() && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-7 h-7 p-0 hover:bg-primary/10"
                >
                  <ChevronDown className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={handleEdit} className="gap-2">
                  <Edit2 className="w-3.5 h-3.5" />
                  Edit BOM
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleViewTree} className="gap-2">
                  <Eye className="w-3.5 h-3.5" />
                  View Tree
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleViewCost} className="gap-2">
                  <DollarSign className="w-3.5 h-3.5" />
                  View Cost
                </DropdownMenuItem>
                <DropdownMenuItem 
                  onClick={(e) => {
                    e.stopPropagation()
                    navigate(`/bom/${activeBom.id}?action=copy`)
                  }}
                  className="gap-2"
                >
                  <Copy className="w-3.5 h-3.5" />
                  Copy BOM
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>

        {/* BOM status and metrics */}
        {isLoading ? (
          <Skeleton className="h-6 w-24" />
        ) : boms.length === 0 ? (
          <div className="flex items-center gap-2">
            <Circle className="w-3 h-3 text-muted-foreground/50" />
            <p className="text-xs text-muted-foreground">No BOMs</p>
          </div>
        ) : (
          <div className="space-y-2.5">
            {/* Version badges */}
            <div className="flex flex-wrap gap-1.5">
              {boms.slice(0, 3).map((bom) => (
                <button
                  key={bom.id}
                  onClick={(e) => {
                    e.stopPropagation()
                    onSelectBom(bom)
                  }}
                  className="inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs hover:bg-accent/50 transition-colors"
                >
                  {bom.is_active ? (
                    <CheckCircle2 className="w-3 h-3 text-green-500" />
                  ) : (
                    <Circle className="w-3 h-3 text-muted-foreground" />
                  )}
                  v{bom.version}
                </button>
              ))}
              {boms.length > 3 && (
                <Badge variant="outline" className="text-xs">
                  +{boms.length - 3}
                </Badge>
              )}
            </div>

            {/* Active BOM details */}
            {activeBom && (
              <div className="pt-1.5 border-t space-y-1.5">
                <Badge className="bg-green-50 text-green-700 border border-green-200 text-xs font-normal">
                  Active: v{activeBom.version}
                </Badge>

                {/* Metrics row */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex items-center justify-between bg-muted/30 px-2 py-1.5 rounded">
                    <span className="text-muted-foreground">Components:</span>
                    <span className="font-semibold">{componentCount}</span>
                  </div>
                  <div className="flex items-center justify-between bg-muted/30 px-2 py-1.5 rounded">
                    <span className="text-muted-foreground">Cost:</span>
                    {costLoading ? (
                      <Skeleton className="h-4 w-12" />
                    ) : (
                      <span className="font-semibold">{currency} {totalCost.toFixed(2)}</span>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
