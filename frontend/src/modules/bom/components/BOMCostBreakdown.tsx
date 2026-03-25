import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  DollarSign, RefreshCw, Loader2, AlertCircle, TrendingUp, Package2, Settings2
} from "lucide-react"
import { bomService } from "@/services/bom.service"
import { BOM } from "@/types/bom.types"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"

interface BOMCostBreakdownProps {
  bom: BOM
}

export function BOMCostBreakdown({ bom }: BOMCostBreakdownProps) {
  const [maxDepth] = useState(20)
  const [refreshKey, setRefreshKey] = useState(0)

  const { data, isLoading, isFetching, isError, error, refetch } = useQuery({
    queryKey: ["bom-cost", bom.id, maxDepth, refreshKey],
    queryFn: () => bomService.getBOMCost(bom.id, maxDepth),
    staleTime: 60_000,
    retry: 1,
  })

  const isRefreshing = isFetching && !isLoading

  const errorMsg =
    (error as any)?.response?.data?.detail ||
    (error as any)?.message ||
    "Failed to calculate cost"

  return (
    <div className="space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-muted-foreground text-sm">
          <DollarSign className="w-4 h-4" />
          <span>Standard Cost Rollup</span>
          {isRefreshing && (
            <span className="flex items-center gap-1 text-xs text-primary">
              <Loader2 className="w-3 h-3 animate-spin" />
              Recalculating...
            </span>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 gap-1.5 text-xs"
          disabled={isFetching}
          onClick={() => {
            setRefreshKey((k) => k + 1)
            refetch()
          }}
        >
          <RefreshCw className={`w-3 h-3 ${isFetching ? "animate-spin" : ""}`} />
          Recalculate
        </Button>
      </div>

      {/* Error state */}
      {isError && (
        <Alert variant="destructive">
          <AlertCircle className="w-4 h-4" />
          <AlertDescription>{errorMsg}</AlertDescription>
        </Alert>
      )}

      {/* Loading state */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
      ) : data ? (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card className="border-green-100 bg-green-50/50">
              <CardHeader className="pb-1 pt-4 px-4">
                <CardTitle className="text-xs text-green-700 font-medium flex items-center gap-1.5">
                  <TrendingUp className="w-3.5 h-3.5" />
                  Total Standard Cost
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                <div className="text-2xl font-bold text-green-800">
                  ${Number(data.total_cost).toFixed(2)}
                </div>
                <p className="text-xs text-green-600 mt-1">
                  All levels included
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-1 pt-4 px-4">
                <CardTitle className="text-xs text-muted-foreground font-medium flex items-center gap-1.5">
                  <Package2 className="w-3.5 h-3.5" />
                  Materials
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                <div className="text-2xl font-bold">
                  ${Number(data.material_cost).toFixed(2)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">Rolled-up components</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-1 pt-4 px-4">
                <CardTitle className="text-xs text-muted-foreground font-medium flex items-center gap-1.5">
                  <Settings2 className="w-3.5 h-3.5" />
                  Operations
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                <div className="text-2xl font-bold">
                  ${Number(data.operation_cost).toFixed(2)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">Routing & Workstations</p>
              </CardContent>
            </Card>
          </div>

          {/* Note if cost is zero */}
          {Number(data.total_cost) === 0 && (
            <Alert>
              <AlertCircle className="w-4 h-4" />
              <AlertDescription>
                Cost is $0.00 — ensure materials have a <strong>current_cost</strong> value set
                and routing operations have a defined run time and workstation rate.
              </AlertDescription>
            </Alert>
          )}
        </>
      ) : null}
    </div>
  )
}
