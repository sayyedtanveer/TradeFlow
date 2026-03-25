import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Box, Plus, Loader2 } from "lucide-react"
import { productService, CreateVariantInput } from "@/services/product.service"
import { ItemTemplate } from "@/types/bom.types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"

interface VariantManagerProps {
  template: ItemTemplate
  canEdit: boolean
}

export function VariantManager({ template, canEdit }: VariantManagerProps) {
  const qc = useQueryClient()
  const [isAdding, setIsAdding] = useState(false)
  const [newValues, setNewValues] = useState<Record<string, string>>({})
  const [standardCost, setStandardCost] = useState("0")
  const [sellingPrice, setSellingPrice] = useState("")

  const { data: variants, isLoading } = useQuery({
    queryKey: ["products", "template", template.id, "variants"],
    queryFn: () => productService.getVariants(template.id, { page_size: 100 }),
    staleTime: 10_000,
  })

  const addMutation = useMutation({
    mutationFn: (payload: CreateVariantInput) => productService.createVariant(template.id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["products", "template", template.id, "variants"] })
      toast.success("Variant created successfully")
      setIsAdding(false)
      setNewValues({})
      setStandardCost("0")
      setSellingPrice("")
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Failed to create variant")
    }
  })

  const handleCreate = () => {
    // Basic validation
    for (const attr of template.attributes) {
      if (!newValues[attr.key]?.trim()) {
        toast.error(`Value for ${attr.label} is required`)
        return
      }
    }
    const cost = parseFloat(standardCost)
    if (isNaN(cost) || cost < 0) {
      toast.error("Standard cost must be >= 0")
      return
    }
    const payload: CreateVariantInput = {
      attribute_values: newValues,
      standard_cost: cost,
      selling_price: sellingPrice ? parseFloat(sellingPrice) : undefined,
    }
    addMutation.mutate(payload)
  }

  // Quick helper to fill a value
  const setVal = (k: string, v: string) => setNewValues(prev => ({ ...prev, [k]: v }))

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-4 border-b pb-2">
         <h2 className="text-base font-medium flex items-center gap-2"><Box className="w-4 h-4"/> Variants ({variants?.total || 0})</h2>
         {!isAdding && canEdit && (
           <Button variant="outline" size="sm" onClick={() => setIsAdding(true)}>
             <Plus className="w-4 h-4 mr-1"/> Add Variant
           </Button>
         )}
      </div>

      {/* Add Variant Form */}
      {isAdding && canEdit && (
        <div className="rounded-lg border bg-muted/20 p-4 space-y-4 mb-4">
          <h4 className="text-sm font-medium">Create New Variant</h4>
          {template.attributes.length === 0 ? (
            <p className="text-xs text-muted-foreground">This template has no dynamic attributes. The variant will act as a standard standalone SKU.</p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {template.attributes.map(attr => (
                <div key={attr.key} className="space-y-1.5">
                  <Label className="text-xs">{attr.label} ({attr.key})</Label>
                  <Input 
                    placeholder="e.g. XL, Blue" 
                    value={newValues[attr.key] || ""} 
                    onChange={e => setVal(attr.key, e.target.value)} 
                  />
                </div>
              ))}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3 pt-2">
            <div className="space-y-1.5">
              <Label className="text-xs">Standard Cost (Required)</Label>
              <Input type="number" min="0" step="0.01" value={standardCost} onChange={e => setStandardCost(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Selling Price (Optional)</Label>
              <Input type="number" min="0" step="0.01" value={sellingPrice} onChange={e => setSellingPrice(e.target.value)} />
            </div>
          </div>

          <div className="flex gap-2 justify-end pt-2">
            <Button variant="ghost" size="sm" onClick={() => setIsAdding(false)}>Cancel</Button>
            <Button size="sm" onClick={handleCreate} disabled={addMutation.isPending}>
              {addMutation.isPending && <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin"/>}
              Create
            </Button>
          </div>
        </div>
      )}

      {/* Variants List */}
      {isLoading ? (
        <div className="text-center py-6 text-muted-foreground"><Loader2 className="w-5 h-5 animate-spin mx-auto"/></div>
      ) : variants?.items.length === 0 && !isAdding ? (
        <div className="text-center py-8 text-sm text-muted-foreground border border-dashed rounded-lg bg-accent/20">
          No variants created yet.
        </div>
      ) : (
        <div className="grid gap-3">
          {variants?.items.map(v => (
            <div key={v.id} className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 border rounded-lg bg-card hover:border-primary/50 transition-colors">
              <div className="flex flex-col min-w-0 flex-1">
                <span className="font-medium text-sm truncate">{v.name}</span>
                <span className="text-xs text-muted-foreground font-mono truncate">{v.code}</span>
                {Object.keys(v.attribute_values).length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {Object.entries(v.attribute_values).map(([k, val]) => (
                      <Badge key={k} variant="secondary" className="text-[10px] px-1.5 py-0 font-normal">
                        {template.attributes.find(a => a.key === k)?.label || k}: {String(val)}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex flex-wrap sm:flex-col gap-x-4 gap-y-1 sm:text-right shrink-0 items-start sm:items-end text-sm">
                <span className="text-green-700 font-medium">Cost: ${v.standard_cost.toFixed(2)}</span>
                {v.selling_price && <span className="text-muted-foreground">Price: ${v.selling_price.toFixed(2)}</span>}
                <Badge variant={v.is_active ? "outline" : "secondary"} className="mt-1">{v.is_active ? "Active" : "Inactive"}</Badge>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
