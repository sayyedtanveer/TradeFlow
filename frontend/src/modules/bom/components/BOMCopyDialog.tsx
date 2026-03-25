import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Loader2, GitBranch, AlertCircle } from "lucide-react"
import { bomService } from "@/services/bom.service"
import { BOM } from "@/types/bom.types"
import { toast } from "sonner"

interface BOMCopyDialogProps {
  open: boolean
  bom: BOM
  productId?: string
  onClose: () => void
  onCopied: (bom: BOM) => void
}

export function BOMCopyDialog({ open, bom, onClose, onCopied }: BOMCopyDialogProps) {
  const [newVersion, setNewVersion] = useState("")

  const { mutate, isPending, isError, error } = useMutation({
    mutationFn: () => bomService.copyBOM(bom.id, newVersion.trim()),
    onSuccess: (copied) => {
      toast.success(`BOM v${copied.version} created successfully`)
      onCopied(copied)
      onClose()
      setNewVersion("")
    },
    onError: () => {
      // error displayed inline
    },
  })

  const errorMsg =
    (error as any)?.response?.data?.detail ||
    (error as any)?.message ||
    "Failed to copy BOM"

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GitBranch className="w-4 h-4" />
            Copy BOM to New Version
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="text-sm text-muted-foreground">
            Copying <span className="font-medium text-foreground">v{bom.version}</span> —
            all components and lines will be duplicated.
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="new-version">New Version Name</Label>
            <Input
              id="new-version"
              placeholder="e.g. 2.0, 1.1-revised"
              value={newVersion}
              onChange={(e) => setNewVersion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && newVersion.trim() && mutate()}
            />
          </div>

          {isError && (
            <Alert variant="destructive">
              <AlertCircle className="w-4 h-4" />
              <AlertDescription>{errorMsg}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isPending}>
            Cancel
          </Button>
          <Button
            onClick={() => mutate()}
            disabled={!newVersion.trim() || isPending}
          >
            {isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            Create Copy
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
