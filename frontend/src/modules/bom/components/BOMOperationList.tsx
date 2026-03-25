import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus, Loader2, GripVertical, AlertCircle } from "lucide-react"
import { bomService } from "@/services/bom.service"
import { BOM } from "@/types/bom.types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

interface BOMOperationListProps {
  bom: BOM
  canEdit: boolean
}

interface AttachForm {
  operation_id: string
  sequence: string
}

export function BOMOperationList({ bom, canEdit }: BOMOperationListProps) {
  const qc = useQueryClient()
  const [form, setForm] = useState<AttachForm>({ operation_id: "", sequence: "" })
  const [showForm, setShowForm] = useState(false)
  const [attachError, setAttachError] = useState<string | null>(null)

  // Fetch available operations
  const { data: operations, isLoading: loadingOps } = useQuery({
    queryKey: ["operations"],
    queryFn: bomService.getOperations,
    staleTime: 60_000,
  })

  // Fetch workstations for name lookup
  const { data: workstations } = useQuery({
    queryKey: ["workstations"],
    queryFn: bomService.getWorkstations,
    staleTime: 60_000,
  })

  // Attach operation mutation
  const attachMutation = useMutation({
    mutationFn: () =>
      bomService.attachOperation(bom.id, {
        operation_id: form.operation_id,
        sequence: parseInt(form.sequence, 10),
      }),
    onSuccess: () => {
      toast.success("Operation attached")
      qc.invalidateQueries({ queryKey: ["bom", bom.id] })
      setForm({ operation_id: "", sequence: "" })
      setShowForm(false)
      setAttachError(null)
    },
    onError: (err: any) => {
      setAttachError(
        err?.response?.data?.detail || err?.message || "Failed to attach operation"
      )
    },
  })

  const getWsName = (wsId: string) =>
    workstations?.find((w) => w.id === wsId)?.name ?? wsId.slice(0, 8) + "..."

  const getOp = (opId: string) =>
    operations?.find((o) => o.id === opId)

  // Derive attached operations from BOM (API returns them as part of BOM or we show placeholder)
  // Since the BOM object doesn't directly carry attached operations (only lines),
  // we show a form to attach and note they're managed server-side.
  const attachedOps = (bom as any).operations as { id: string; operation_id: string; sequence: number }[] | undefined

  const usedSequences = new Set(attachedOps?.map((o) => o.sequence) ?? [])

  const nextSequence = () => {
    if (!attachedOps || attachedOps.length === 0) return "10"
    return String(Math.max(...attachedOps.map((o) => o.sequence)) + 10)
  }

  return (
    <div className="space-y-4">
      {/* Operations table */}
      {loadingOps ? (
        <div className="space-y-2">
          {[1, 2].map((i) => <Skeleton key={i} className="h-12 w-full rounded-md" />)}
        </div>
      ) : !attachedOps || attachedOps.length === 0 ? (
        <div className="flex flex-col items-center justify-center border border-dashed rounded-lg py-10 gap-2 text-muted-foreground">
          <GripVertical className="w-6 h-6" />
          <p className="text-sm">No operations attached to this BOM.</p>
          {canEdit && (
            <Button variant="outline" size="sm" onClick={() => { setShowForm(true); setForm((f) => ({ ...f, sequence: nextSequence() })) }}>
              <Plus className="w-3.5 h-3.5 mr-1.5" />
              Attach First Operation
            </Button>
          )}
        </div>
      ) : (
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 border-b">
              <tr>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground w-16">Seq</th>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground">Operation</th>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground hidden md:table-cell">Workstation</th>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground hidden sm:table-cell">Setup</th>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground hidden sm:table-cell">Run</th>
              </tr>
            </thead>
            <tbody>
              {[...attachedOps]
                .sort((a, b) => a.sequence - b.sequence)
                .map((ao) => {
                  const op = getOp(ao.operation_id)
                  return (
                    <tr key={ao.id} className="border-b last:border-0 hover:bg-accent/30">
                      <td className="px-3 py-2">
                        <Badge variant="outline" className="font-mono text-xs">
                          {ao.sequence}
                        </Badge>
                      </td>
                      <td className="px-3 py-2 font-medium">{op?.name ?? "Unknown"}</td>
                      <td className="px-3 py-2 text-muted-foreground hidden md:table-cell">
                        {op ? getWsName(op.workstation_id) : "—"}
                      </td>
                      <td className="px-3 py-2 text-muted-foreground hidden sm:table-cell">
                        {op ? `${op.setup_time}m` : "—"}
                      </td>
                      <td className="px-3 py-2 text-muted-foreground hidden sm:table-cell">
                        {op ? `${op.run_time}m/unit` : "—"}
                      </td>
                    </tr>
                  )
                })}
            </tbody>
          </table>
        </div>
      )}

      {/* Attach form */}
      {canEdit && (
        <div className="space-y-3">
          {!showForm ? (
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={() => { setShowForm(true); setForm((f) => ({ ...f, sequence: nextSequence() })) }}
            >
              <Plus className="w-3.5 h-3.5 mr-1.5" />
              Attach Operation
            </Button>
          ) : (
            <div className="rounded-lg border bg-muted/20 p-4 space-y-3">
              <h4 className="text-sm font-medium">Attach New Operation</h4>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* Operation selector */}
                <div className="space-y-1.5 sm:col-span-1">
                  <Label>Operation</Label>
                  {loadingOps ? (
                    <Skeleton className="h-9 w-full" />
                  ) : (
                    <Select
                      value={form.operation_id}
                      onValueChange={(v) => setForm((f) => ({ ...f, operation_id: v }))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select operation..." />
                      </SelectTrigger>
                      <SelectContent>
                        {(operations ?? []).map((op) => (
                          <SelectItem key={op.id} value={op.id}>
                            <span className="font-medium">{op.name}</span>
                            <span className="text-muted-foreground text-xs ml-2">
                              @ {getWsName(op.workstation_id)}
                            </span>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>

                {/* Sequence — manual input */}
                <div className="space-y-1.5">
                  <Label>
                    Sequence
                    <span className="text-xs text-muted-foreground ml-1">(manual)</span>
                  </Label>
                  <Input
                    type="number"
                    min={1}
                    step={10}
                    placeholder="e.g. 10, 20, 30"
                    value={form.sequence}
                    onChange={(e) => setForm((f) => ({ ...f, sequence: e.target.value }))}
                    className={cn(
                      usedSequences.has(parseInt(form.sequence, 10)) && form.sequence
                        ? "border-destructive"
                        : ""
                    )}
                  />
                  {usedSequences.has(parseInt(form.sequence, 10)) && form.sequence && (
                    <p className="text-xs text-destructive flex items-center gap-1">
                      <AlertCircle className="w-3 h-3" />
                      Sequence already in use
                    </p>
                  )}
                </div>
              </div>

              {attachError && (
                <Alert variant="destructive">
                  <AlertCircle className="w-4 h-4" />
                  <AlertDescription>{attachError}</AlertDescription>
                </Alert>
              )}

              <div className="flex gap-2 justify-end">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => { setShowForm(false); setAttachError(null) }}
                  disabled={attachMutation.isPending}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={() => attachMutation.mutate()}
                  disabled={
                    !form.operation_id ||
                    !form.sequence ||
                    isNaN(parseInt(form.sequence, 10)) ||
                    attachMutation.isPending
                  }
                >
                  {attachMutation.isPending && (
                    <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                  )}
                  Attach
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
