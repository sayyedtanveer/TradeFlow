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
import { Plus, ScanBarcode, AlertCircle } from "lucide-react"
import { useSearchParams } from "react-router-dom"
import { ColumnDef } from "@tanstack/react-table"
import { usePermissions } from "@/hooks/usePermissions"
import { ProductFormDrawer } from "../components/ProductFormDrawer"
import { useToast } from "@/hooks/use-toast"
import { formatCurrency } from "@/utils/currency"

export default function ProductListPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { canWrite } = usePermissions()
  const { toast } = useToast()
  
  const productId = searchParams.get("productId")
  const filter = searchParams.get("filter")
  const isDrawerOpen = productId !== null

  const handleCloseDrawer = () => {
    setSearchParams({})
  }

  const { data: products, isLoading, error, isError } = useQuery({
    queryKey: ["products"],
    queryFn: () => inventoryService.getProducts(),
  })

  // Show error toast if query fails
  if (isError && error && !isLoading) {
    toast({
      title: "Error loading products",
      description: error instanceof Error ? error.message : "Failed to load products. Please try again.",
      variant: "destructive",
    })
  }

  // Filter products based on query parameters
  const filteredProducts = useMemo(() => {
    if (!products) return []
    if (filter === "low-stock") {
      return products.filter(p => (p.stock_quantity ?? 0) <= p.reorder_point)
    }
    return products
  }, [products, filter])

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

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-destructive mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <p className="font-medium text-destructive">Failed to load products</p>
            <p className="text-sm text-destructive/80 mt-1">
              {error instanceof Error ? error.message : "An error occurred while loading products. Please try again."}
            </p>
          </div>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => window.location.reload()}
            className="mt-0"
          >
            Retry
          </Button>
        </div>
      )}

      {isLoading ? (
        <TableSkeleton rows={8} />
      ) : (
        <>
          <div className="hidden md:block">
            <DataTable 
              columns={columns} 
              data={filteredProducts || []} 
              searchKey="name" 
              searchPlaceholder="Search products by name..."
            />
          </div>
          <div className="md:hidden grid gap-4 grid-cols-1 sm:grid-cols-2">
            {(filteredProducts || []).map((product) => {
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
                      <div className="font-semibold bg-primary/10 text-primary px-2 py-1 rounded text-sm">{formatCurrency(product.price)}</div>
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
