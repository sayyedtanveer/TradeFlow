import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Trash2, Plus, Edit2, Check, X, Package2, Box, Layers } from "lucide-react"
import { bomService } from "@/services/bom.service"
import { BOM, BOMLine, BOMLineInput } from "@/types/bom.types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

import { BOMLineForm } from "./BOMLineForm"
import { toast } from "sonner"


interface BOMLineListProps {
  bom: BOM
  canEdit: boolean
}

export function BOMLineList({ bom, canEdit }: BOMLineListProps) {
  const qc = useQueryClient()
  const [isAdding, setIsAdding] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editQty, setEditQty] = useState("")
  const [editScrap, setEditScrap] = useState("")

  const updateMutation = useMutation({
    mutationFn: (newLines: BOMLineInput[]) =>
      bomService.updateBOM(bom.id, { lines: newLines }),
    onSuccess: (updated) => {
      qc.setQueryData(["bom", bom.id], updated)
      qc.invalidateQueries({ queryKey: ["bom-tree", bom.id] })
      qc.invalidateQueries({ queryKey: ["bom-cost", bom.id] })
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Failed to update BOM lines")
    },
  })

  // Map existing BOMLine to BOMLineInput
  const getLinesInput = (): BOMLineInput[] => {
    return bom.lines.map((l) => ({
      material_id: l.material_id || undefined,
      template_id: l.template_id || undefined,
      variant_id: l.variant_id || undefined,
      quantity: l.quantity,
      scrap_percentage: l.scrap_percentage,
      unit_id: l.unit_id || undefined,
    }))
  }

  const handleAddLine = async (line: BOMLineInput) => {
    const newLines = [...getLinesInput(), line]
    await updateMutation.mutateAsync(newLines)
    setIsAdding(false)
    toast.success("Component added")
  }

  const handleRemoveLine = async (index: number) => {
    const newLines = getLinesInput()
    newLines.splice(index, 1)
    await updateMutation.mutateAsync(newLines)
    toast.success("Component removed")
  }

  const startEdit = (line: BOMLine) => {
    setEditingId(line.id)
    setEditQty(line.quantity.toString())
    setEditScrap((line.scrap_percentage || 0).toString())
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditQty("")
    setEditScrap("")
  }

  const saveEdit = async (index: number) => {
    const q = parseFloat(editQty)
    const s = parseFloat(editScrap)
    if (isNaN(q) || q <= 0) {
      toast.error("Quantity must be greater than 0")
      return
    }

    const newLines = getLinesInput()
    newLines[index].quantity = q
    newLines[index].scrap_percentage = isNaN(s) ? 0 : s

    await updateMutation.mutateAsync(newLines)
    setEditingId(null)
    toast.success("Component updated")
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between px-1">
        <h3 className="text-sm font-medium">Direct Components</h3>
        {canEdit && !isAdding && (
          <Button size="sm" onClick={() => setIsAdding(true)} className="h-8">
            <Plus className="w-3.5 h-3.5 mr-1.5" />
            Add Component
          </Button>
        )}
      </div>

      {isAdding && canEdit && (
        <BOMLineForm onAdd={handleAddLine} onCancel={() => setIsAdding(false)} />
      )}

      {bom.lines.length === 0 && !isAdding ? (
        <div className="text-center py-6 border border-dashed rounded-lg text-sm text-muted-foreground">
          No components in this BOM.
        </div>
      ) : (
        <div className="rounded-md border overflow-hidden">
          <div className="overflow-x-auto min-w-0">
            <table className="w-full text-sm">
            <thead className="bg-muted/50 border-b">
              <tr>
                <th className="h-9 px-3 text-left font-medium text-muted-foreground w-12">Type</th>
                <th className="h-9 px-3 text-left font-medium text-muted-foreground min-w-40">Component</th>
                <th className="h-9 px-3 text-right font-medium text-muted-foreground w-28">Qty</th>
                <th className="h-9 px-3 text-right font-medium text-muted-foreground w-24">Scrap %</th>
                <th className="h-9 px-3 text-right font-medium text-muted-foreground w-24">Edit</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {bom.lines.map((line, idx) => {
                const isEditing = editingId === line.id
                const targetId = line.material_id || line.variant_id || line.template_id
                let type: "material" | "template" | "variant" = "material"
                if (line.template_id) type = "template"
                else if (line.variant_id) type = "variant"

                return (
                  <tr key={line.id} className={`group hover:bg-muted/20 transition-colors ${isEditing ? 'bg-blue-50 dark:bg-blue-950/20 border-l-2 border-l-blue-500' : ''}`}>
                    <td className="p-3">
                      {type === "material" ? (
                        <Package2 className="w-4 h-4 text-amber-600" />
                      ) : type === "template" ? (
                        <Layers className="w-4 h-4 text-blue-600" />
                      ) : (
                        <Box className="w-4 h-4 text-violet-600" />
                      )}
                    </td>
                    <td className="p-3">
                      <div className="flex flex-col gap-0.5">
                        <span className="font-medium text-xs truncate">{targetId?.split("-")[0]}...</span>
                        <span className="text-xs text-muted-foreground capitalize">{type}</span>
                      </div>
                    </td>
                    <td className="p-3 text-right">
                      {isEditing ? (
                        <div className="flex items-center justify-end gap-1">
                          <Input
                            type="number"
                            step="0.001"
                            className="h-7 w-20 text-right font-semibold border-blue-500 focus:border-blue-600"
                            value={editQty}
                            onChange={(e) => setEditQty(e.target.value)}
                          />
                        </div>
                      ) : (
                        <span className="font-medium">{parseFloat(line.quantity.toString()).toFixed(3)}</span>
                      )}
                    </td>
                    <td className="p-3 text-right">
                      {isEditing ? (
                        <Input
                          type="number"
                          step="0.01"
                          className="h-7 w-16 text-right border-blue-500 focus:border-blue-600"
                          value={editScrap}
                          onChange={(e) => setEditScrap(e.target.value)}
                        />
                      ) : (
                        <span className={`font-medium ${(line.scrap_percentage ?? 0) > 0 ? "text-amber-600 font-semibold" : "text-muted-foreground"}`}>
                          {parseFloat((line.scrap_percentage || 0).toString()).toFixed(2)}%
                        </span>
                      )}
                    </td>
                    <td className="p-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {isEditing ? (
                          <>
                            <Button 
                              variant="default" 
                              size="sm"
                              className="bg-green-600 hover:bg-green-700" 
                              onClick={() => saveEdit(idx)}
                              title="Save changes"
                            >
                              <Check className="w-4 h-4" />
                            </Button>
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={cancelEdit}
                              title="Cancel edit"
                            >
                              <X className="w-4 h-4" />
                            </Button>
                          </>
                        ) : canEdit ? (
                          <>
                            <Button 
                              variant="ghost" 
                              size="sm"
                              className="opacity-0 group-hover:opacity-100 transition-opacity" 
                              onClick={() => startEdit(line)}
                              title="Edit line"
                            >
                              <Edit2 className="w-4 h-4" />
                            </Button>
                            <Button 
                              variant="ghost" 
                              size="sm"
                              className="opacity-0 group-hover:opacity-100 transition-opacity text-destructive hover:bg-destructive/10" 
                              onClick={() => handleRemoveLine(idx)}
                              title="Delete line"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </Button>
                          </>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          </div>
        </div>
      )}
    </div>
  )
}
