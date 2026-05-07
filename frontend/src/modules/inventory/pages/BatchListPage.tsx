import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { format } from "date-fns"
import { ColumnDef } from "@tanstack/react-table"
import { PageHeader } from "@/components/layout/PageHeader"
import { DataTable } from "@/components/shared/DataTable"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { TableSkeleton } from "@/components/shared/LoadingSkeleton"
import { Card, CardContent } from "@/components/ui/card"
import { materialService } from "@/services/material.service"
import type { Batch, Material } from "@/types/material.types"

function formatDate(value: string | null) {
  return value ? format(new Date(value), "MMM d, yyyy") : "-"
}

function batchBadge(batch: Batch) {
  if (batch.is_expired) {
    return <StatusBadge status="expired" label="Expired" />
  }
  if (batch.days_until_expiry !== null && batch.days_until_expiry <= 14) {
    return <StatusBadge status="pending" label={`Expires in ${batch.days_until_expiry}d`} />
  }
  return <StatusBadge status="active" label={batch.status || "Active"} />
}

export default function BatchListPage() {
  const { data: batches = [], isLoading: isLoadingBatches } = useQuery({
    queryKey: ["batches", "expiring"],
    queryFn: () => materialService.getExpiringBatches(60),
  })

  const { data: materialsData, isLoading: isLoadingMaterials } = useQuery({
    queryKey: ["materials", "batch-list"],
    queryFn: () => materialService.getMaterials({ page: 1, page_size: 500 }),
  })

  const materialLookup = useMemo(() => {
    return new Map<string, Material>((materialsData?.items || []).map((material) => [material.id, material]))
  }, [materialsData])

  const columns = useMemo<ColumnDef<Batch>[]>(() => [
    {
      accessorKey: "batch_number",
      header: "Batch No",
      cell: ({ row }) => <span className="font-mono font-medium">{row.original.batch_number}</span>,
    },
    {
      accessorKey: "material_id",
      header: "Item",
      cell: ({ row }) => {
        const material = materialLookup.get(row.original.material_id)
        return (
          <div>
            <p className="font-medium">{material?.code || "Unknown item"}</p>
            <p className="text-xs text-muted-foreground">{material?.name || "Material no longer available"}</p>
          </div>
        )
      },
    },
    {
      accessorKey: "remaining_quantity",
      header: "Remaining",
      cell: ({ row }) => <span className="font-mono">{row.original.remaining_quantity}</span>,
    },
    {
      accessorKey: "created_at",
      header: "Received",
      cell: ({ row }) => formatDate(row.original.created_at),
    },
    {
      accessorKey: "expiry_date",
      header: "Expiry Status",
      cell: ({ row }) => batchBadge(row.original),
    },
  ], [materialLookup])

  const isLoading = isLoadingBatches || isLoadingMaterials

  return (
    <div className="w-full space-y-6">
      <PageHeader
        title="Batch Tracking"
        description="Monitor batch quantities and expiration dates from live inventory records."
      />

      {isLoading ? (
        <TableSkeleton rows={8} />
      ) : (
        <>
          <div className="hidden md:block">
            <DataTable
              columns={columns}
              data={batches}
              searchKey="batch_number"
              searchPlaceholder="Search by batch code..."
            />
          </div>
          <div className="grid gap-4 md:hidden">
            {batches.map((batch) => {
              const material = materialLookup.get(batch.material_id)
              return (
                <Card key={batch.id}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="font-medium">{material?.name || "Material no longer available"}</h3>
                        <p className="text-sm font-mono text-muted-foreground">
                          {material?.code || "Unknown item"} / {batch.batch_number}
                        </p>
                      </div>
                      {batchBadge(batch)}
                    </div>
                    <div className="mt-4 flex justify-between text-sm">
                      <span className="text-muted-foreground">
                        Qty: <span className="font-medium text-foreground">{batch.remaining_quantity}</span>
                      </span>
                      <span className="text-muted-foreground">
                        Expiry: <span className="text-foreground">{formatDate(batch.expiry_date)}</span>
                      </span>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
            {batches.length === 0 && (
              <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                No expiring batches found.
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
