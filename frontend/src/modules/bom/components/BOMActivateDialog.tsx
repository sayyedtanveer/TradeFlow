import { useMutation } from "@tanstack/react-query"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Loader2, Zap, AlertCircle, CheckCircle2, Package2 } from "lucide-react"
import { bomService } from "@/services/bom.service"
import { BOM } from "@/types/bom.types"
import { toast } from "sonner"

interface BOMActivateDialogProps {
  open: boolean
  bom: BOM
  onClose: () => void
  onActivated: (bom: BOM) => void
}

function getValidationErrors(bom: BOM): string[] {
  const errors: string[] = []
  if (!bom.lines || bom.lines.length === 0) {
    errors.push("BOM has no component lines. Add at least one component before activating.")
  }
  if (!bom.valid_from) {
    errors.push("BOM has no 'Valid From' date set.")
  }
  const now = new Date()
  if (bom.valid_to && new Date(bom.valid_to) < now) {
    errors.push(`BOM validity expired on ${new Date(bom.valid_to).toLocaleDateString()}.`)
  }
  return errors
}

export function BOMActivateDialog({ open, bom, onClose, onActivated }: BOMActivateDialogProps) {
  const validationErrors = getValidationErrors(bom)
  const canActivate = validationErrors.length === 0

  const { mutate, isPending, isError, error } = useMutation({
    mutationFn: () => bomService.activateBOM(bom.id),
    onSuccess: (activated) => {
      toast.success(`BOM v${activated.version} is now active`)
      onActivated(activated)
      onClose()
    },
  })

  const apiError =
    (error as any)?.response?.data?.detail ||
    (error as any)?.message

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-500" />
            Activate BOM v{bom.version}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Validation checks */}
          {validationErrors.length > 0 ? (
            <Alert variant="destructive">
              <AlertCircle className="w-4 h-4" />
              <AlertTitle>Cannot activate — validation failed</AlertTitle>
              <AlertDescription>
                <ul className="mt-1 space-y-1 list-disc list-inside text-sm">
                  {validationErrors.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          ) : (
            <Alert className="border-green-200 bg-green-50 text-green-800">
              <CheckCircle2 className="w-4 h-4 text-green-600" />
              <AlertTitle className="text-green-700">Ready to activate</AlertTitle>
              <AlertDescription className="text-green-600">
                All validation checks passed.
              </AlertDescription>
            </Alert>
          )}

          {/* Summary */}
          <div className="rounded-lg border bg-muted/30 p-3 space-y-1.5 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Version</span>
              <span className="font-medium">v{bom.version}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Components</span>
              <span className="font-medium flex items-center gap-1">
                <Package2 className="w-3.5 h-3.5" />
                {bom.lines.length}
              </span>
            </div>
            {bom.valid_from && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Valid From</span>
                <span className="font-medium">
                  {new Date(bom.valid_from).toLocaleDateString()}
                </span>
              </div>
            )}
          </div>

          <p className="text-xs text-muted-foreground">
            Activating this BOM will <strong>deactivate any currently active version</strong>{" "}
            for this product.
          </p>

          {isError && apiError && (
            <Alert variant="destructive">
              <AlertCircle className="w-4 h-4" />
              <AlertDescription>{apiError}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isPending}>
            Cancel
          </Button>
          <Button
            onClick={() => mutate()}
            disabled={!canActivate || isPending}
            className="bg-green-600 hover:bg-green-700"
          >
            {isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            <Zap className="w-4 h-4 mr-2" />
            Confirm Activate
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
