import { useNavigate, useParams } from "react-router-dom"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { inventoryService } from "@/services/inventory.service"
import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { FormSkeleton } from "@/components/shared/LoadingSkeleton"
import { ArrowLeft, Save } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

const productSchema = z.object({
  sku: z.string().min(3, "SKU must be at least 3 characters"),
  name: z.string().min(2, "Name is required"),
  description: z.string().optional(),
  category: z.string().min(1, "Category is required"),
  reorder_point: z.coerce.number().min(0),
  price: z.coerce.number().min(0),
})

type ProductFormValues = z.infer<typeof productSchema>

export default function ProductFormPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const isEditing = Boolean(id && id !== "new")

  const { data: product, isLoading: isFetching } = useQuery({
    queryKey: ["product", id],
    queryFn: () => inventoryService.getProduct(id!),
    enabled: isEditing,
  })

  // Using raw uncontrolled form approach with react-hook-form register for simplicity in Phase 1
  // Can be mapped to shadcn Form components later if needed
  const { register, handleSubmit, formState: { errors }, setValue, watch } = useForm<ProductFormValues>({
    resolver: zodResolver(productSchema),
    values: product ? {
      sku: product.sku,
      name: product.name,
      description: product.description || "",
      category: product.category,
      reorder_point: product.reorder_point,
      price: product.price,
    } : {
      sku: "",
      name: "",
      description: "",
      category: "",
      reorder_point: 10,
      price: 0,
    }
  })

  const saveMutation = useMutation({
    mutationFn: async (data: ProductFormValues) => {
      // Mock API call
      await new Promise(resolve => setTimeout(resolve, 800))
      return { id: isEditing ? id : Math.random().toString(), ...data }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] })
      navigate("/inventory/products")
    }
  })

  const onSubmit = (data: ProductFormValues) => {
    saveMutation.mutate(data)
  }

  if (isEditing && isFetching) {
    return (
      <div className="space-y-6">
        <PageHeader title="Edit Product" />
        <FormSkeleton fields={5} />
      </div>
    )
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/inventory/products")}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <PageHeader 
          title={isEditing ? "Edit Product" : "New Product"} 
          description={isEditing ? `Update details for ${product?.name}` : "Add a new item to your inventory catalog."}
          action={
            <Button onClick={handleSubmit(onSubmit)} disabled={saveMutation.isPending}>
              <Save className="mr-2 h-4 w-4" />
              {saveMutation.isPending ? "Saving..." : "Save Product"}
            </Button>
          }
        />
      </div>

      <div className="grid gap-6 p-6 border rounded-xl bg-card">
        <div className="grid sm:grid-cols-2 gap-4 border-b pb-6">
          <div className="space-y-2">
            <Label htmlFor="sku">SKU / Barcode</Label>
            <Input id="sku" placeholder="E.g. RW-001" {...register("sku")} />
            {errors.sku && <p className="text-xs text-destructive">{errors.sku.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="name">Product Name</Label>
            <Input id="name" placeholder="E.g. Raw Material A" {...register("name")} />
            {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          </div>
        </div>

        <div className="space-y-2 border-b pb-6">
          <Label htmlFor="description">Description (Optional)</Label>
          <Textarea id="description" rows={3} {...register("description")} />
        </div>

        <div className="grid sm:grid-cols-3 gap-4">
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
    </div>
  )
}
