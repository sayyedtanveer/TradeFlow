import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { inventoryService } from "@/services/inventory.service"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { FormSkeleton } from "@/components/shared/LoadingSkeleton"
import { Save } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Drawer } from "@/components/shared/Drawer"
import { useEffect } from "react"

const productSchema = z.object({
  sku: z.string().min(3, "SKU must be at least 3 characters"),
  name: z.string().min(2, "Name is required"),
  description: z.string().optional(),
  category: z.string().min(1, "Category is required"),
  reorder_point: z.coerce.number().min(0),
  price: z.coerce.number().min(0),
})

type ProductFormValues = z.infer<typeof productSchema>

interface Props {
  productId: string | null
  open: boolean
  onClose: () => void
}

export function ProductFormDrawer({ productId, open, onClose }: Props) {
  const queryClient = useQueryClient()
  const isEditing = Boolean(productId && productId !== "new")

  const { data: product, isLoading: isFetching } = useQuery({
    queryKey: ["product", productId],
    queryFn: () => inventoryService.getProduct(productId!),
    enabled: isEditing && open,
  })

  // Using raw uncontrolled form approach with react-hook-form register for simplicity in Phase 1
  const { register, handleSubmit, formState: { errors }, setValue, watch, reset } = useForm<ProductFormValues>({
    resolver: zodResolver(productSchema),
    defaultValues: {
      sku: "",
      name: "",
      description: "",
      category: "",
      reorder_point: 10,
      price: 0,
    }
  })

  // Reset form when product data loads or modal opens for "new"
  useEffect(() => {
    if (product) {
      reset({
        sku: product.sku,
        name: product.name,
        description: product.description || "",
        category: product.category,
        reorder_point: product.reorder_point,
        price: product.price,
      })
    } else if (productId === "new") {
      reset({
        sku: "",
        name: "",
        description: "",
        category: "",
        reorder_point: 10,
        price: 0,
      })
    }
  }, [product, productId, reset])

  const saveMutation = useMutation({
    mutationFn: async (data: ProductFormValues) => {
      await new Promise(resolve => setTimeout(resolve, 800))
      return { id: isEditing ? productId : Math.random().toString(), ...data }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] })
      onClose()
    }
  })

  const onSubmit = (data: ProductFormValues) => {
    saveMutation.mutate(data)
  }

  return (
    <Drawer 
      open={open} 
      onOpenChange={(v) => !v && onClose()} 
      title={isEditing ? "Edit Product" : "New Product"}
      description={isEditing ? `Update details for ${product?.name || "product"}` : "Add a new item to your inventory catalog."}
    >
      {isEditing && isFetching ? (
        <FormSkeleton fields={5} />
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 pb-8">
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="sku">SKU / Barcode</Label>
              <Input id="sku" placeholder="E.g. RW-001" {...register("sku")} autoFocus />
              {errors.sku && <p className="text-xs text-destructive">{errors.sku.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="name">Product Name</Label>
              <Input id="name" placeholder="E.g. Raw Material A" {...register("name")} />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description (Optional)</Label>
              <Textarea id="description" rows={3} {...register("description")} />
            </div>

            <div className="space-y-2">
              <Label htmlFor="category">Category</Label>
              <Select 
                value={watch("category")} 
                onValueChange={(val) => setValue("category", val, { shouldValidate: true })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select Category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Raw Materials">Raw Materials</SelectItem>
                  <SelectItem value="Packaging">Packaging</SelectItem>
                  <SelectItem value="Finished Goods">Finished Goods</SelectItem>
                  <SelectItem value="Consumables">Consumables</SelectItem>
                </SelectContent>
              </Select>
              {errors.category && <p className="text-xs text-destructive">{errors.category.message}</p>}
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="reorder_point">Reorder Point</Label>
                <Input id="reorder_point" type="number" min="0" {...register("reorder_point")} />
                {errors.reorder_point && <p className="text-xs text-destructive">{errors.reorder_point.message}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="price">Unit Price</Label>
                <Input id="price" type="number" step="0.01" min="0" {...register("price")} />
                {errors.price && <p className="text-xs text-destructive">{errors.price.message}</p>}
              </div>
            </div>
          </div>
          
          <div className="pt-4 flex gap-3 w-full sm:justify-end">
            <Button type="button" variant="outline" onClick={onClose} className="w-full sm:w-auto">Cancel</Button>
            <Button type="submit" disabled={saveMutation.isPending} className="w-full sm:w-auto">
              <Save className="mr-2 h-4 w-4" />
              {saveMutation.isPending ? "Saving..." : "Save Product"}
            </Button>
          </div>
        </form>
      )}
    </Drawer>
  )
}
