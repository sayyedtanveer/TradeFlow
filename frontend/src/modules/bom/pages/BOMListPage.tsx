import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import {
  Layers, Search, ChevronRight, CheckCircle2, Circle, AlertCircle
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

// We list BOMs by fetching templates first, then their BOMs
export default function BOMListPage() {
  const navigate = useNavigate()
  const { canEditBOM } = usePermissions()
  const [search, setSearch] = useState("")

  const { data: tplData, isLoading, isError } = useQuery({
    queryKey: ["bom-list-templates"],
    queryFn: () => bomService.getTemplates({ page_size: 100 }),
    staleTime: 30_000,
  })

  const templates = tplData?.items ?? []
  const filtered = search
    ? templates.filter(
        (t) =>
          t.name.toLowerCase().includes(search.toLowerCase()) ||
          t.code.toLowerCase().includes(search.toLowerCase())
      )
    : templates

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

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-muted-foreground" />
        <Input
          className="pl-8"
          placeholder="Search products..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {isError && (
        <Alert variant="destructive">
          <AlertCircle className="w-4 h-4" />
          <AlertDescription>Failed to load product list.</AlertDescription>
        </Alert>
      )}

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground border border-dashed rounded-xl">
          <Layers className="w-10 h-10" />
          <p className="text-sm">No products found. Create item templates first.</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((tpl) => (
            <TemplateCard
              key={tpl.id}
              templateId={tpl.id}
              name={tpl.name}
              code={tpl.code}
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
  onClick,
  onSelectBom,
}: {
  templateId: string
  name: string
  code: string
  onClick: () => void
  onSelectBom: (bom: BOM) => void
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["bom-versions", templateId, true],
    queryFn: () => bomService.getBOMsForProduct(templateId, true),
    staleTime: 30_000,
  })

  const boms = data?.items ?? []
  const activeBom = boms.find((b) => b.is_active)

  return (
    <Card
      className="cursor-pointer hover:border-primary/50 hover:bg-accent/20 transition-all group"
      onClick={onClick}
    >
      <CardContent className="p-4 space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="font-semibold text-sm truncate">{name}</h3>
            <p className="text-xs text-muted-foreground font-mono">{code}</p>
          </div>
          <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0 group-hover:text-primary transition-colors mt-0.5" />
        </div>

        {/* BOM status summary */}
        {isLoading ? (
          <Skeleton className="h-6 w-24" />
        ) : boms.length === 0 ? (
          <p className="text-xs text-muted-foreground">No BOMs</p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {boms.slice(0, 4).map((bom) => (
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
            {boms.length > 4 && (
              <Badge variant="outline" className="text-xs">
                +{boms.length - 4} more
              </Badge>
            )}
          </div>
        )}

        {/* Active badge */}
        {activeBom && (
          <Badge className="bg-green-50 text-green-700 border border-green-200 text-xs font-normal">
            Active: v{activeBom.version}
          </Badge>
        )}
      </CardContent>
    </Card>
  )
}
