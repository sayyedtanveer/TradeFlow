import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  IndianRupee, RefreshCw, Loader2, AlertCircle, TrendingUp, Package2, Settings2,
  ChevronDown, ChevronUp
} from "lucide-react"
import { bomService } from "@/services/bom.service"
import { BOM, BOMTreeNode } from "@/types/bom.types"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { formatCurrency } from "@/utils/currency"

interface BOMCostBreakdownProps {
  bom: BOM
}

export function BOMCostBreakdown({ bom }: BOMCostBreakdownProps) {
  const [maxDepth] = useState(20)
  const [refreshKey, setRefreshKey] = useState(0)
  const [expandMaterials, setExpandMaterials] = useState(true)
  const [expandOperations, setExpandOperations] = useState(false)

  const { data, isLoading, isFetching, isError, error, refetch } = useQuery({
    queryKey: ["bom-cost", bom.id, maxDepth, refreshKey],
    queryFn: () => bomService.getBOMCost(bom.id, maxDepth),
    staleTime: 60_000,
    retry: 1,
  })

  const { data: treeData, isLoading: treeLoading } = useQuery({
    queryKey: ["bom-tree", bom.id, maxDepth],
    queryFn: () => bomService.getBOMTree(bom.id, { max_depth: maxDepth }),
    staleTime: 60_000,
    retry: 1,
  })

  const { data: operationsList } = useQuery({
    queryKey: ["operations"],
    queryFn: bomService.getOperations,
    staleTime: 60_000,
  })

  const { data: workstationsList } = useQuery({
    queryKey: ["workstations"],
    queryFn: bomService.getWorkstations,
    staleTime: 60_000,
  })

  const isRefreshing = isFetching && !isLoading

  const errorMsg =
    (error as any)?.response?.data?.detail ||
    (error as any)?.message ||
    "Failed to calculate cost"

  // Helper function to extract material nodes from BOM tree
  const getMaterialNodes = (node: BOMTreeNode, materials: BOMTreeNode[] = []): BOMTreeNode[] => {
    if (node.type === "material") {
      materials.push(node)
    }
    if (node.children) {
      node.children.forEach((child) => getMaterialNodes(child, materials))
    }
    return materials
  }

  return (
    <div className="space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-muted-foreground text-sm">
          <IndianRupee className="w-4 h-4" />
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
            <Card className="border-green-100 bg-gradient-to-br from-green-50 to-green-100/30">
              <CardHeader className="pb-1 pt-4 px-4">
                <CardTitle className="text-xs text-green-700 font-medium flex items-center gap-1.5">
                  <TrendingUp className="w-3.5 h-3.5" />
                  Total Standard Cost
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4 space-y-2">
                <div className="text-2xl sm:text-3xl font-bold text-green-800 truncate">
                  {formatCurrency(data.total_cost, data.currency_symbol || "₹")}
                </div>
                <p className="text-xs text-green-600">
                  All levels included
                </p>
              </CardContent>
            </Card>

            <Card className="hover:border-primary/30 transition-colors">
              <CardHeader className="pb-1 pt-4 px-4">
                <CardTitle className="text-xs text-muted-foreground font-medium flex items-center gap-1.5">
                  <Package2 className="w-3.5 h-3.5" />
                  Materials
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4 space-y-2">
                <div className="text-xl sm:text-2xl font-bold text-amber-700 truncate">
                  {formatCurrency(data.material_cost, data.currency_symbol || "₹")}
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-muted-foreground">Percentage</span>
                    <span className="font-semibold">
                      {Number(data.total_cost) > 0
                        ? ((data.material_cost / data.total_cost) * 100).toFixed(1)
                        : 0}%
                    </span>
                  </div>
                  {/* Progress bar */}
                  <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-amber-500 h-full transition-all"
                      style={{
                        width: Number(data.total_cost) > 0
                          ? `${(data.material_cost / data.total_cost) * 100}%`
                          : "0%",
                      }}
                    />
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">Rolled-up components</p>
              </CardContent>
            </Card>

            <Card className="hover:border-primary/30 transition-colors">
              <CardHeader className="pb-1 pt-4 px-4">
                <CardTitle className="text-xs text-muted-foreground font-medium flex items-center gap-1.5">
                  <Settings2 className="w-3.5 h-3.5" />
                  Operations
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4 space-y-2">
                <div className="text-xl sm:text-2xl font-bold text-blue-700 truncate">
                  {formatCurrency(data.operation_cost, data.currency_symbol || "₹")}
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-muted-foreground">Percentage</span>
                    <span className="font-semibold">
                      {Number(data.total_cost) > 0
                        ? ((data.operation_cost / data.total_cost) * 100).toFixed(1)
                        : 0}%
                    </span>
                  </div>
                  {/* Progress bar */}
                  <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-blue-500 h-full transition-all"
                      style={{
                        width: Number(data.total_cost) > 0
                          ? `${(data.operation_cost / data.total_cost) * 100}%`
                          : "0%",
                      }}
                    />
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">Routing & workstations</p>
              </CardContent>
            </Card>
          </div>

          {/* Detailed breakdown - Materials */}
          {!treeLoading && treeData && (
            <div className="space-y-3 border-t pt-4">
              <button
                onClick={() => setExpandMaterials(!expandMaterials)}
                className="w-full flex items-center justify-between p-3 bg-muted/40 hover:bg-muted/60 transition-colors rounded-lg"
              >
                <div className="flex items-center gap-2 font-medium text-sm">
                  <Package2 className="w-4 h-4 text-amber-600" />
                  <span>Material Cost Breakdown</span>
                  <span className="text-xs text-muted-foreground">
                    ({getMaterialNodes(treeData).length} items)
                  </span>
                </div>
                {expandMaterials ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </button>

              {expandMaterials && (
                <div className="rounded-lg border overflow-hidden">
                  <div className="overflow-x-auto min-w-0">
                    <Table className="text-sm">
                    <TableHeader className="bg-muted/50">
                      <TableRow>
                        <TableHead className="text-xs">Item</TableHead>
                        <TableHead className="text-xs text-right">Qty</TableHead>
                        <TableHead className="text-xs text-right">Unit Cost</TableHead>
                        <TableHead className="text-xs text-right">Total Cost</TableHead>
                        <TableHead className="text-xs text-right">% of Total</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {getMaterialNodes(treeData)
                        .sort((a, b) => (b.cost || 0) - (a.cost || 0))
                        .map((node) => {
                          const itemCost = node.cost || 0
                          const pct =
                            Number(data.total_cost) > 0
                              ? ((itemCost / data.total_cost) * 100).toFixed(1)
                              : "0"
                          const unitCost =
                            node.quantity > 0 ? itemCost / node.quantity : 0
                          return (
                            <TableRow
                              key={node.id}
                              className="hover:bg-muted/30 transition-colors"
                            >
                              <TableCell className="text-xs font-medium">
                                <div className="flex flex-col gap-0.5">
                                  <span>{node.name}</span>
                                  <span className="text-xs text-muted-foreground">
                                    {node.code}
                                  </span>
                                </div>
                              </TableCell>
                              <TableCell className="text-xs text-right">
                                {node.quantity}
                                {node.unit && ` ${node.unit}`}
                              </TableCell>
                              <TableCell className="text-xs text-right">
                                {data.currency_symbol || "₹"} {unitCost.toFixed(4)}
                              </TableCell>
                              <TableCell className="text-xs text-right font-semibold">
                                {formatCurrency(itemCost, data.currency_symbol || "₹")}
                              </TableCell>
                              <TableCell className="text-xs text-right text-amber-600">
                                {pct}%
                              </TableCell>
                            </TableRow>
                          )
                        })}
                    </TableBody>
                  </Table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Detailed breakdown - Operations Estimate */}
          {expandOperations && Number(data.operation_cost) > 0 && (
            <div className="space-y-3 border-t pt-4">
              <button
                onClick={() => setExpandOperations(!expandOperations)}
                className="w-full flex items-center justify-between p-3 bg-muted/40 hover:bg-muted/60 transition-colors rounded-lg"
              >
                <div className="flex items-center gap-2 font-medium text-sm">
                  <Settings2 className="w-4 h-4 text-blue-600" />
                  <span>Operation Cost Breakdown</span>
                </div>
                {expandOperations ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </button>

              {expandOperations && (
                <div className="rounded-lg border overflow-hidden mt-3">
                  <div className="overflow-x-auto min-w-0">
                    <Table className="text-sm">
                      <TableHeader className="bg-muted/50">
                        <TableRow>
                          <TableHead className="text-xs">Operation</TableHead>
                          <TableHead className="text-xs text-right">Time (min)</TableHead>
                          <TableHead className="text-xs text-right">Workstation Rate</TableHead>
                          <TableHead className="text-xs text-right">Operation Cost</TableHead>
                          <TableHead className="text-xs text-right">% of Total</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(bom.operations || []).map((bomOp) => {
                          const op = operationsList?.find((o) => o.id === bomOp.operation_id)
                          const ws = workstationsList?.find((w) => w.id === op?.workstation_id)
                          const totalTime = (op?.setup_time || 0) + (op?.run_time || 0)
                          const hourlyRate = ws?.hourly_rate || 0
                          const opCost = totalTime * (hourlyRate / 60)
                          
                          const pct = Number(data.total_cost) > 0 
                            ? ((opCost / data.total_cost) * 100).toFixed(1) 
                            : "0.0"

                          return (
                            <TableRow key={bomOp.id} className="hover:bg-muted/30 transition-colors">
                              <TableCell className="text-xs font-medium">
                                <div className="flex flex-col gap-0.5">
                                  <span>{op ? op.name : "Unknown Operation"}</span>
                                  <span className="text-xs text-muted-foreground">
                                    {ws ? ws.name : "Unknown Workstation"}
                                  </span>
                                </div>
                              </TableCell>
                              <TableCell className="text-xs text-right text-muted-foreground">
                                {totalTime}
                              </TableCell>
                              <TableCell className="text-xs text-right text-muted-foreground">
                                {data.currency_symbol || "₹"} {hourlyRate.toFixed(2)}/hr
                              </TableCell>
                              <TableCell className="text-xs text-right font-semibold">
                                {formatCurrency(opCost, data.currency_symbol || "₹")}
                              </TableCell>
                              <TableCell className="text-xs text-right text-blue-600">
                                {pct}%
                              </TableCell>
                            </TableRow>
                          )
                        })}
                        {(!bom.operations || bom.operations.length === 0) && (
                          <TableRow>
                            <TableCell colSpan={5} className="text-center text-muted-foreground py-4">
                              No direct operations attached to this BOM entirely.
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Toggle for operations section when no operations */}
          {!expandOperations && Number(data.operation_cost) > 0 && (
            <div className="border-t pt-4">
              <button
                onClick={() => setExpandOperations(true)}
                className="w-full flex items-center justify-between p-3 bg-muted/40 hover:bg-muted/60 transition-colors rounded-lg"
              >
                <div className="flex items-center gap-2 font-medium text-sm">
                  <Settings2 className="w-4 h-4 text-blue-600" />
                  <span>Operation Cost Breakdown</span>
                </div>
                <ChevronDown className="w-4 h-4" />
              </button>
            </div>
          )}
        </>
      ) : null}
    </div>
  )
}
