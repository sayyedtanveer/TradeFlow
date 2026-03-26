import { useQuery } from "@tanstack/react-query"
import { useMemo } from "react"
import { inventoryService } from "@/services/inventory.service"
import { Product } from "@/types/inventory.types"
import { DataTable } from "@/components/shared/DataTable"
import { PageHeader } from "@/components/layout/PageHeader"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { TableSkeleton } from "@/components/shared/LoadingSkeleton"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Plus, ScanBarcode } from "lucide-react"
import { useSearchParams } from "react-router-dom"
import { ColumnDef } from "@tanstack/react-table"
import { usePermissions } from "@/hooks/usePermissions"
import { ProductFormDrawer } from "../components/ProductFormDrawer"

export default function ProductListPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { canWrite } = usePermissions()
  
  const productId = searchParams.get("productId")
  const isDrawerOpen = productId !== null

  const handleCloseDrawer = () => {
    setSearchParams({})
  }

  const { data: products, isLoading } = useQuery({
    queryKey: ["products"],
    queryFn: () => inventoryService.getProducts(),
  })

  // Define columns for TanStack Table
  const columns = useMemo<ColumnDef<Product>[]>(() => [
    {
      accessorKey: "sku",
      header: "SKU / Barcode",
      cell: ({ row }) => <span className="font-medium text-primary">{row.original.sku}</span>,
    },
    {
      accessorKey: "name",
      header: "Product Name",
    },
    {
      accessorKey: "category",
      header: "Category",
    },
    {
      accessorKey: "stock_quantity",
      header: "Stock",
      cell: ({ row }) => {
        const product = row.original
        const qty = product.stock_quantity ?? 0
        const isLow = qty <= product.reorder_point
        return (
          <div className="flex items-center gap-2">
            <span className={isLow ? "text-destructive font-medium" : ""}>{qty}</span>
            {isLow && <StatusBadge status="low-stock" label="Low" />}
          </div>
        )
      },
    },
    {
      accessorKey: "price",
      header: "Price",
      cell: ({ row }) => {
        // Minimal format for currency for now, replace with formatCurrency util later
        return `$${row.original.price.toFixed(2)}`
      },
    },
    {
      id: "actions",
      cell: ({ row }) => {
        return (
          <Button variant="ghost" size="sm" onClick={() => setSearchParams({ productId: row.original.id })}>
            View
          </Button>
        )
      },
    },
  ], [setSearchParams])

  const actionButtons = (
    <>
      {canWrite() && (
        <Button variant="outline" onClick={() => setSearchParams({ action: "scan" })}>
          <ScanBarcode className="mr-2 h-4 w-4" />
          Scan Product
        </Button>
      )}
      {canWrite() && (
        <Button onClick={() => setSearchParams({ productId: "new" })}>
          <Plus className="mr-2 h-4 w-4" />
          Add Product
        </Button>
      )}
    </>
  )

  return (
    <div className="w-full space-y-6">
      <PageHeader 
        title="Products" 
        description="Manage your inventory catalog, pricing, and stock levels."
        action={actionButtons}
      />

      {isLoading ? (
        <TableSkeleton rows={8} />
      ) : (
        <>
          <div className="hidden md:block">
            <DataTable 
              columns={columns} 
              data={products || []} 
              searchKey="name" 
              searchPlaceholder="Search products by name..."
            />
          </div>
          <div className="md:hidden grid gap-4 grid-cols-1 sm:grid-cols-2">
            {(products || []).map((product) => {
              const qty = product.stock_quantity ?? 0;
              const isLow = qty <= product.reorder_point;
              
              return (
                <Card key={product.id} className="cursor-pointer hover:bg-accent/50 transition-colors" onClick={() => setSearchParams({ productId: product.id })}>
                  <CardContent className="p-4">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h3 className="font-medium text-base">{product.name}</h3>
                        <p className="text-xs text-muted-foreground font-mono">{product.sku}</p>
                      </div>
                      <div className="font-semibold bg-primary/10 text-primary px-2 py-1 rounded text-sm">${product.price.toFixed(2)}</div>
                    </div>
                    <div className="flex justify-between items-end mt-4">
                      <span className="text-sm text-muted-foreground">{product.category}</span>
                      <div className="flex items-center gap-2">
                        <span className={isLow ? "text-destructive font-medium text-sm" : "text-sm font-medium"}>
                          {qty} in stock
                        </span>
                        {isLow && (
                          <StatusBadge status="low-stock" label="Low" />
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </>
      )}
      
      <ProductFormDrawer 
        open={isDrawerOpen} 
        onClose={handleCloseDrawer} 
        productId={productId} 
      />
    </div>
  )
}
