import { PageHeader } from "@/components/layout/PageHeader"
import { DataTable } from "@/components/shared/DataTable"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { Card, CardContent } from "@/components/ui/card"
import { ColumnDef } from "@tanstack/react-table"
import { addDays, format } from "date-fns"

// Dummy data for batches
type Batch = {
  id: string
  batch_number: string
  product_name: string
  quantity: number
  manufacturing_date: string
  expiry_date: string
}

const mockBatches: Batch[] = [
  { id: "1", batch_number: "LOT-2023-A", product_name: "Raw Material A", quantity: 500, manufacturing_date: new Date().toISOString(), expiry_date: addDays(new Date(), 30).toISOString() },
  { id: "2", batch_number: "LOT-2023-B", product_name: "Active Ingredient X", quantity: 42, manufacturing_date: new Date().toISOString(), expiry_date: addDays(new Date(), 5).toISOString() },
  { id: "3", batch_number: "LOT-2023-C", product_name: "Packaging Box", quantity: 1200, manufacturing_date: new Date().toISOString(), expiry_date: addDays(new Date(), 365).toISOString() },
]

export default function BatchListPage() {
  const columns: ColumnDef<Batch>[] = [
    {
      accessorKey: "batch_number",
      header: "Batch No",
    },
    {
      accessorKey: "product_name",
      header: "Product",
    },
    {
      accessorKey: "quantity",
      header: "Quantity",
    },
    {
      accessorKey: "manufacturing_date",
      header: "Mfg Date",
      cell: ({ row }) => format(new Date(row.original.manufacturing_date), "MMM d, yyyy"),
    },
    {
      accessorKey: "expiry_date",
      header: "Expiry Status",
      cell: ({ row }) => {
        const expiry = new Date(row.original.expiry_date)
        const daysToExpiry = Math.floor((expiry.getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24))
        
        // Custom logic for batch expiration badges
        if (daysToExpiry < 0) {
          return <StatusBadge status="expired" label="Expired" />
        } else if (daysToExpiry <= 14) {
          return <StatusBadge status="pending" label={`Expires in ${daysToExpiry}d`} />
        } else {
          return <StatusBadge status="active" label="Valid" />
        }
      },
    },
  ]

  return (
    <div className="w-full space-y-6">
      <PageHeader 
        title="Batch Tracking" 
        description="Monitor LOT numbers and expiration dates for your stock."
      />
      
      <div className="hidden md:block">
        <DataTable 
          columns={columns} 
          data={mockBatches} 
          searchKey="batch_number" 
          searchPlaceholder="Search by Batch code..."
        />
      </div>
      <div className="md:hidden grid gap-4 grid-cols-1">
        {mockBatches.map((batch) => {
          const expiry = new Date(batch.expiry_date)
          const daysToExpiry = Math.floor((expiry.getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24))
          
          let badge;
          if (daysToExpiry < 0) {
            badge = <StatusBadge status="expired" label="Expired" />
          } else if (daysToExpiry <= 14) {
            badge = <StatusBadge status="pending" label={`Expires in ${daysToExpiry}d`} />
          } else {
            badge = <StatusBadge status="active" label="Valid" />
          }

          return (
            <Card key={batch.id}>
              <CardContent className="p-4">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <h3 className="font-medium">{batch.product_name}</h3>
                    <p className="text-sm text-muted-foreground font-mono">{batch.batch_number}</p>
                  </div>
                  {badge}
                </div>
                <div className="flex justify-between mt-4 text-sm">
                  <span className="text-muted-foreground">Qty: <span className="font-medium text-foreground">{batch.quantity}</span></span>
                  <span className="text-muted-foreground">Mfg: <span className="text-foreground">{format(new Date(batch.manufacturing_date), "MMM d, yyyy")}</span></span>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
