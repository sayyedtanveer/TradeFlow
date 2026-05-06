import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { materialService } from "@/services/material.service"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { FormSkeleton } from "@/components/shared/LoadingSkeleton"
import { Save } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Drawer } from "@/components/shared/Drawer"
import { useEffect } from "react"
import { supplyChainApi } from "@/services/supply-chain.service"
import { Checkbox } from "@/components/ui/checkbox"

const GENERIC_RAW_NAMES = new Set([
  "raw material",
  "raw materials",
  "material",
  "materials",
  "component",
  "components",
  "item",
  "items",
])

const GENERIC_FINISHED_NAMES = new Set([
  "finished good",
  "finished goods",
  "product",
  "products",
  "final product",
  "finished item",
  "goods",
  "item",
  "items",
])

const normalizeMaterialName = (value: string) =>
  value.trim().replace(/\s+/g, " ").toLowerCase()

const materialSchema = z.object({
  code: z.string().trim().min(1, "Code must be at least 1 character").max(100),
  name: z.string().trim().min(1, "Name is required").max(255),
  material_type: z.enum(["raw", "finished"]),
  base_unit_id: z.string().uuid("Please select a valid unit").nullable().optional(),
  description: z.string().max(2000).optional().nullable(),
  category_id: z.string().uuid("Please select a valid category").nullable().optional(),
  reorder_level: z.coerce.number().min(0).optional().nullable(),
  location_id: z.string().uuid("Please select a valid location").nullable().optional(),
  is_batch_tracked: z.boolean().default(false).optional(),
  is_serialized: z.boolean().default(false).optional(),
  inspection_required: z.boolean().optional(),
  inspection_template_id: z.string().uuid().nullable().optional(),
}).superRefine(({ name, material_type }, ctx) => {
  const normalized = normalizeMaterialName(name)
  if (material_type === "raw" && GENERIC_RAW_NAMES.has(normalized)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["name"],
      message: "Use the actual raw material name, for example Brass Body, Glass Tube, or O-Ring Seal.",
    })
  }
  if (material_type === "finished" && GENERIC_FINISHED_NAMES.has(normalized)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["name"],
      message: "Use the actual finished good name, for example Gear Rotameter - Standard.",
    })
  }
})

type MaterialFormValues = z.infer<typeof materialSchema>

interface Props {
  materialId: string | null
  open: boolean
  onClose: () => void
}

export function MaterialFormDrawer({ materialId, open, onClose }: Props) {
  const queryClient = useQueryClient()
  const isEditing = Boolean(materialId && materialId !== "new")

  const { data: material, isLoading: isFetchingMaterial } = useQuery({
    queryKey: ["material", materialId],
    queryFn: () => materialService.getMaterial(materialId!),
    enabled: isEditing && open,
  })

  const { data: categories, isLoading: isFetchingCategories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => materialService.getCategories(),
  })

  const { data: units, isLoading: isFetchingUnits } = useQuery({
    queryKey: ["units"],
    queryFn: () => materialService.getUnits(),
  })

  const { data: locations, isLoading: isFetchingLocations } = useQuery({
    queryKey: ["locations"],
    queryFn: () => materialService.getLocations(),
  })

  const { data: inspectionTemplates } = useQuery({
    queryKey: ["inspection-templates"],
    queryFn: () => supplyChainApi.listInspectionTemplates().then((r) => r.data),
    enabled: open && isEditing,
  })

  const isFetching = isFetchingMaterial || isFetchingCategories || isFetchingUnits || isFetchingLocations;

  const { register, handleSubmit, formState: { errors }, setValue, watch, reset } = useForm<MaterialFormValues>({
    resolver: zodResolver(materialSchema),
    defaultValues: {
      code: "",
      name: "",
      material_type: "raw",
      base_unit_id: null,
      description: "",
      category_id: null,
      reorder_level: 10,
      location_id: null,
      is_batch_tracked: false,
      is_serialized: false,
      inspection_required: false,
      inspection_template_id: null,
    }
  })

  // Reset form when material data loads or modal opens for "new"
  useEffect(() => {
    if (material) {
      reset({
        code: material.code,
        name: material.name,
        material_type: (material.material_type as "raw" | "finished") || "raw",
        base_unit_id: material.base_unit_id || null,
        description: material.description || "",
        category_id: material.category_id || null,
        reorder_level: material.reorder_level ?? 10,
        location_id: material.location_id || null,
        is_batch_tracked: material.is_batch_tracked ?? false,
        is_serialized: material.is_serialized ?? false,
        inspection_required: material.inspection_required ?? false,
        inspection_template_id: material.inspection_template_id || null,
      })
    } else if (materialId === "new") {
      reset({
        code: "",
        name: "",
        material_type: "raw",
        base_unit_id: null,
        description: "",
        category_id: null,
        reorder_level: 10,
        location_id: null,
        is_batch_tracked: false,
        is_serialized: false,
        inspection_required: false,
        inspection_template_id: null,
      })
    }
  }, [material, materialId, reset])

  const saveMutation = useMutation({
    mutationFn: async (data: MaterialFormValues) => {
      if (isEditing) {
        return await materialService.updateMaterial(materialId!, {
          name: data.name,
          description: data.description,
          category_id: data.category_id,
          base_unit_id: data.base_unit_id,
          material_type: data.material_type,
          reorder_level: data.reorder_level,
          location_id: data.location_id,
          is_batch_tracked: data.is_batch_tracked,
          is_serialized: data.is_serialized,
          inspection_required: data.inspection_required,
          inspection_template_id: data.inspection_template_id ?? null,
        })
      } else {
        return await materialService.createMaterial({
          code: data.code,
          name: data.name,
          material_type: data.material_type,
          base_unit_id: data.base_unit_id,
          description: data.description,
          category_id: data.category_id,
          reorder_level: data.reorder_level,
          location_id: data.location_id,
          is_batch_tracked: data.is_batch_tracked,
          is_serialized: data.is_serialized,
        })
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["materials"] })
      onClose()
    }
  })

  const onSubmit = (data: MaterialFormValues) => {
    saveMutation.mutate(data)
  }

  const selectedMaterialType = watch("material_type") || "raw"
  const namePlaceholder =
    selectedMaterialType === "raw" ? "E.g. Brass Body" : "E.g. Gear Rotameter - Standard"
  const namingHint =
    selectedMaterialType === "raw"
      ? "Use the actual component name. Avoid generic labels like Raw Material."
      : "Use the finished product name shown to sales, planning, and clients."

  return (
    <Drawer 
      open={open} 
      onOpenChange={(v) => !v && onClose()} 
      title={isEditing ? "Edit Material" : "New Material"}
      description={isEditing ? `Update details for ${material?.name || "material"}` : "Add a new material to your inventory catalog."}
    >
      {(isEditing && isFetching) ? (
         <FormSkeleton fields={5} />
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 pb-8">
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="code">Material Code</Label>
                <Input id="code" placeholder="E.g. MAT-001" {...register("code")} disabled={isEditing} autoFocus={!isEditing} />
                {errors.code && <p className="text-xs text-destructive">{errors.code.message}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="base_unit_id">Base Unit</Label>
                <Select 
                  value={watch("base_unit_id") || ""} 
                  onValueChange={(val) => setValue("base_unit_id", val, { shouldValidate: true })}
                >
                  <SelectTrigger disabled={isEditing}>
                    <SelectValue placeholder="Select Base Unit" />
                  </SelectTrigger>
                  <SelectContent>
                    {units?.map((u) => (
                      <SelectItem key={u.id} value={u.id}>
                        {u.name} ({u.code})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.base_unit_id && <p className="text-xs text-destructive">{errors.base_unit_id.message}</p>}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">Material Name</Label>
                <Input id="name" placeholder={namePlaceholder} {...register("name")} autoFocus={isEditing} />
                {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
                {!errors.name && <p className="text-xs text-muted-foreground">{namingHint}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="material_type">Material Type</Label>
                <Select 
                  value={watch("material_type") || "raw"} 
                  onValueChange={(val) => setValue("material_type", val as "raw" | "finished", { shouldValidate: true })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="raw">Raw Material</SelectItem>
                    <SelectItem value="finished">Finished Good</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description (Optional)</Label>
              <Textarea id="description" rows={3} {...register("description")} />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="category_id">Category</Label>
                <Select 
                  value={watch("category_id") || ""} 
                  onValueChange={(val) => setValue("category_id", val, { shouldValidate: true })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Category" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories?.map((c) => (
                      <SelectItem key={c.id} value={c.id}>
                        {c.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.category_id && <p className="text-xs text-destructive">{errors.category_id.message}</p>}
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="location_id">Storage Location</Label>
                <Select 
                  value={watch("location_id") || ""} 
                  onValueChange={(val) => setValue("location_id", val, { shouldValidate: true })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Storage" />
                  </SelectTrigger>
                  <SelectContent>
                    {locations?.map((l) => (
                      <SelectItem key={l.id} value={l.id}>
                        {l.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.location_id && <p className="text-xs text-destructive">{errors.location_id.message}</p>}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="reorder_level">Reorder Level</Label>
              <Input id="reorder_level" type="number" min="0" step="0.01" {...register("reorder_level")} />
              {errors.reorder_level && <p className="text-xs text-destructive">{errors.reorder_level.message}</p>}
            </div>

            {isEditing && (
              <div className="space-y-3 border-t pt-4">
                <p className="text-sm font-medium">Receiving / inspection</p>
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="insp_req"
                    checked={watch("inspection_required")}
                    onCheckedChange={(v) => setValue("inspection_required", v === true, { shouldValidate: true })}
                  />
                  <Label htmlFor="insp_req" className="font-normal cursor-pointer">
                    Inspection required
                  </Label>
                </div>
                <div className="space-y-2">
                  <Label>Inspection template</Label>
                  <Select
                    value={watch("inspection_template_id") || "__none__"}
                    onValueChange={(v) =>
                      setValue("inspection_template_id", v === "__none__" ? null : v, { shouldValidate: true })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="None" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none__">(none)</SelectItem>
                      {(inspectionTemplates ?? []).map((t) => (
                        <SelectItem key={t.id} value={t.id}>
                          {t.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}
          </div>
          
          <div className="pt-4 flex gap-3 w-full sm:justify-end">
            <Button type="button" variant="outline" onClick={onClose} className="w-full sm:w-auto">Cancel</Button>
            <Button type="submit" disabled={saveMutation.isPending} className="w-full sm:w-auto">
              <Save className="mr-2 h-4 w-4" />
              {saveMutation.isPending ? "Saving..." : "Save Material"}
            </Button>
          </div>
        </form>
      )}
    </Drawer>
  )
}
