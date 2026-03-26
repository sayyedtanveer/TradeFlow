import { useState, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { Search, Package2, AlertCircle, Loader } from "lucide-react"
import { bomService } from "@/services/bom.service"
import { ItemTemplate, ItemVariant } from "@/types/bom.types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Skeleton } from "@/components/ui/skeleton"
import { Label } from "@/components/ui/label"

interface ProductSelectionModalProps {
  onSelect: (product: ItemTemplate | ItemVariant, isTemplate: boolean) => void
  onCancel: () => void
}

type Product = (ItemTemplate & { _type: "template" }) | (ItemVariant & { _type: "variant" })

export function ProductSelectionModal({ onSelect, onCancel }: ProductSelectionModalProps) {
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedId, setSelectedId] = useState<string>("")

  // Fetch templates
  const { 
    data: templatesData, 
    isLoading: isLoadingTemplates, 
    isError: isErrorTemplates 
  } = useQuery({
    queryKey: ["bom-templates"],
    queryFn: () => bomService.getTemplates({ page_size: 100 }),
    staleTime: 30_000,
  })

  // Fetch variants
  const { 
    data: variantsData, 
    isLoading: isLoadingVariants, 
    isError: isErrorVariants 
  } = useQuery({
    queryKey: ["bom-variants"],
    queryFn: () => bomService.getAllVariants({ page_size: 100 }),
    staleTime: 30_000,
  })

  const templates = templatesData?.items ?? []
  const variants = variantsData?.items ?? []
  const isLoading = isLoadingTemplates || isLoadingVariants
  const isError = isErrorTemplates || isErrorVariants

  // Combine and filter products
  const allProducts: Product[] = useMemo(() => {
    const tpls = templates.map(t => ({ ...t, _type: "template" as const }))
    const vars = variants.map(v => ({ ...v, _type: "variant" as const }))
    return [...tpls, ...vars]
  }, [templates, variants])

  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return allProducts
    const q = searchQuery.toLowerCase()
    return allProducts.filter(p => 
      p.name.toLowerCase().includes(q) || 
      p.code.toLowerCase().includes(q) ||
      (p._type === "variant" && p.variant_key?.toLowerCase().includes(q))
    )
  }, [allProducts, searchQuery])

  const handleSelect = () => {
    const product = allProducts.find(p => p.id === selectedId)
    if (product) {
      const isTemplate = product._type === "template"
      const { _type, ...rest } = product
      onSelect(rest as any, isTemplate)
    }
  }

  return (
    <div className="w-full max-w-2xl space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold">Select Product</h2>
        <p className="text-muted-foreground mt-1">
          Search by product name, code, or variant code
        </p>
      </div>

      {/* Search Input */}
      <div className="space-y-2">
        <Label htmlFor="product-search">Search Products</Label>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            id="product-search"
            placeholder="e.g. Widget, PROD-001, storage_capacity_128gb"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <Skeleton key={i} className="h-16 rounded-lg" />
          ))}
        </div>
      )}

      {/* Error State */}
      {isError && (
        <Alert variant="destructive">
          <AlertCircle className="w-4 h-4" />
          <AlertDescription>
            Failed to load products. Please try again.
          </AlertDescription>
        </Alert>
      )}

      {/* Empty State */}
      {!isLoading && !isError && filtered.length === 0 && (
        <Alert>
          <AlertCircle className="w-4 h-4" />
          <AlertDescription>
            {searchQuery ? 
              "No products match your search" : 
              "No products available. Please create a product template first."
            }
          </AlertDescription>
        </Alert>
      )}

      {/* Product List */}
      {!isLoading && !isError && filtered.length > 0 && (
        <div className="border rounded-lg bg-card overflow-hidden">
          <div className="max-h-96 overflow-y-auto">
            {filtered.map(product => (
              <button
                key={product.id}
                onClick={() => setSelectedId(product.id)}
                className={`w-full px-4 py-3 text-left border-b last:border-b-0 transition-colors ${
                  selectedId === product.id
                    ? "bg-primary/5 border-primary"
                    : "hover:bg-muted/50"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Package2 className="w-4 h-4 flex-shrink-0 text-muted-foreground" />
                      <h3 className="font-medium truncate">{product.name}</h3>
                      <Badge variant={product._type === "template" ? "default" : "secondary"} className="flex-shrink-0">
                        {product._type === "template" ? "Template" : "Variant"}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground flex items-center gap-2">
                      <span className="font-mono">{product.code}</span>
                      {product._type === "variant" && product.variant_key && (
                        <>
                          <span>•</span>
                          <span className="font-mono text-xs">{product.variant_key}</span>
                        </>
                      )}
                    </p>
                  </div>
                  <div className={`w-5 h-5 rounded border-2 flex-shrink-0 mt-0.5 transition-all ${
                    selectedId === product.id
                      ? "bg-primary border-primary"
                      : "border-muted-foreground"
                  }`} />
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3 justify-end pt-4">
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button 
          onClick={handleSelect}
          disabled={!selectedId || isLoading}
        >
          {isLoading ? (
            <>
              <Loader className="w-4 h-4 mr-2 animate-spin" />
              Loading...
            </>
          ) : (
            "Select Product"
          )}
        </Button>
      </div>
    </div>
  )
}
