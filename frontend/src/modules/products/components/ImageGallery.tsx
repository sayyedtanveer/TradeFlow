import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Upload, Trash2, Star, GripVertical } from "lucide-react"
import { productService } from "@/services/product.service"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"

interface ImageGalleryProps {
  template_id: string
  variant_id?: string
  canEdit?: boolean
}

export function ImageGallery({ template_id, variant_id, canEdit = true }: ImageGalleryProps) {
  const qc = useQueryClient()
  const [uploading, setUploading] = useState(false)

  const queryKey = variant_id 
    ? ["products", "variant", variant_id, "images"]
    : ["products", "template", template_id, "images"]

  // Load images
  const { data: images, isLoading } = useQuery({
    queryKey,
    queryFn: () =>
      variant_id
        ? productService.getVariantImages(variant_id)
        : productService.getTemplateImages(template_id),
  })

  // Upload image
  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      if (variant_id) {
        return productService.uploadVariantImage(template_id, variant_id, file)
      } else {
        return productService.uploadTemplateImage(template_id, file)
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey })
      toast.success("Image uploaded successfully")
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Upload failed")
    },
  })

  // Set primary
  const setPrimaryMutation = useMutation({
    mutationFn: (imageId: string) => productService.setPrimaryImage(imageId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey })
      toast.success("Primary image updated")
    },
  })

  // Delete image
  const deleteMutation = useMutation({
    mutationFn: (imageId: string) => productService.deleteImage(imageId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey })
      toast.success("Image deleted")
    },
  })

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setUploading(true)
      try {
        await uploadMutation.mutateAsync(file)
      } finally {
        setUploading(false)
      }
    }
  }

  if (isLoading) return <div className="text-center py-8 text-muted-foreground">Loading images...</div>

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="font-semibold">Images ({images?.items.length || 0})</h3>
        {canEdit && (
          <label>
            <input
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              disabled={uploading}
              className="hidden"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={(e) => (e.currentTarget.parentElement?.querySelector("input") as HTMLInputElement)?.click()}
              disabled={uploading}
            >
              <Upload className="w-4 h-4 mr-1" />
              {uploading ? "Uploading..." : "Add Image"}
            </Button>
          </label>
        )}
      </div>

      {!images?.items.length ? (
        <div className="text-center py-8 border border-dashed rounded-lg text-muted-foreground">
          No images yet. {canEdit && "Click 'Add Image' to upload."}
        </div>
      ) : (
        <div className="grid grid-cols-6 gap-4">
          {images.items.map((img) => (
            <div key={img.id} className="relative group">
              <div className="aspect-square rounded-lg overflow-hidden bg-muted">
                <img src={img.file_path} alt={img.file_name} className="w-full h-full object-cover" />
              </div>
              {img.is_primary && (
                <div className="absolute top-1 right-1 bg-blue-600 text-white p-1 rounded-full">
                  <Star className="w-3 h-3 fill-current" />
                </div>
              )}
              {canEdit && (
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition rounded-lg flex items-center justify-center gap-1">
                  {!img.is_primary && (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-white hover:bg-white/20"
                      onClick={() => setPrimaryMutation.mutate(img.id)}
                      title="Set as primary"
                    >
                      <Star className="w-4 h-4" />
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-white hover:bg-red-600/50"
                    onClick={() => deleteMutation.mutate(img.id)}
                    title="Delete image"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
