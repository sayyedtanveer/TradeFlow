import { useEffect, useState } from "react"
import { materialService } from "@/services/material.service"
import type { Location } from "@/types/material.types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useToast } from "@/hooks/use-toast"

function locKind(l: Location & { location_type?: string }) {
  return l.location_type ?? (l as { type?: string }).type ?? ""
}

type Props = {
  /** When false, list is read-only (e.g. storekeeper). */
  canManage: boolean
  /** All locations (for parent warehouse names). */
  allLocations: (Location & { location_type?: string })[]
}

export function QuarantineLocationList({ canManage, allLocations }: Props) {
  const { toast } = useToast()
  const [rows, setRows] = useState<(Location & { location_type?: string })[]>([])
  const [name, setName] = useState("")
  const [code, setCode] = useState("")
  const [parentId, setParentId] = useState("")

  const warehouses = allLocations.filter((l) => locKind(l) === "warehouse" && l.is_active)

  const load = () =>
    materialService.getLocations({ type: "quarantine" }).then((r) => {
      setRows(r as (Location & { location_type?: string })[])
    })

  useEffect(() => {
    load().catch(() => toast({ title: "Failed to load quarantine locations", variant: "destructive" }))
  }, [toast])

  const parentName = (pid: string | null | undefined) => {
    if (!pid) return "—"
    const p = allLocations.find((x) => x.id === pid)
    return p?.name ?? String(pid).slice(0, 8)
  }

  const create = async () => {
    if (!canManage) return
    if (!name.trim()) {
      toast({ title: "Name required", variant: "destructive" })
      return
    }
    try {
      await materialService.createLocation({
        name: name.trim(),
        type: "quarantine",
        code: code.trim() || undefined,
        parent_id: parentId || undefined,
        is_active: true,
      })
      toast({ title: "Quarantine location created" })
      setName("")
      setCode("")
      setParentId("")
      await load()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast({ title: detail || "Create failed", variant: "destructive" })
    }
  }

  const deactivate = async (id: string) => {
    if (!canManage) return
    try {
      await materialService.updateLocation(id, { is_active: false })
      toast({ title: "Location deactivated" })
      await load()
    } catch {
      toast({ title: "Update failed", variant: "destructive" })
    }
  }

  return (
    <div className="space-y-6">
      {canManage ? (
        <div className="border rounded-lg p-4 space-y-3 max-w-lg">
          <h3 className="font-medium">Add quarantine location</h3>
          <p className="text-xs text-muted-foreground">
            Used when inspection fails (API: POST /inventory/master-data/locations with type quarantine).
          </p>
          <div className="space-y-2">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Q1 — hold" />
          </div>
          <div className="space-y-2">
            <Label>Code (optional)</Label>
            <Input value={code} onChange={(e) => setCode(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Parent warehouse (optional)</Label>
            <Select value={parentId || "__none__"} onValueChange={(v) => setParentId(v === "__none__" ? "" : v)}>
              <SelectTrigger>
                <SelectValue placeholder="None" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">(none)</SelectItem>
                {warehouses.map((l) => (
                  <SelectItem key={l.id} value={l.id}>
                    {l.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button type="button" onClick={create}>
            Create
          </Button>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">You have read-only access to quarantine locations.</p>
      )}

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Code</TableHead>
            <TableHead>Parent</TableHead>
            <TableHead>Active</TableHead>
            {canManage && <TableHead className="w-[100px]" />}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((l) => (
            <TableRow key={l.id}>
              <TableCell>{l.name}</TableCell>
              <TableCell className="font-mono text-xs">{l.code || "—"}</TableCell>
              <TableCell>{parentName(l.parent_location_id ?? l.parent_id)}</TableCell>
              <TableCell>{l.is_active ? "yes" : "no"}</TableCell>
              {canManage && (
                <TableCell>
                  {l.is_active && (
                    <Button variant="outline" size="sm" type="button" onClick={() => deactivate(l.id)}>
                      Deactivate
                    </Button>
                  )}
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {rows.length === 0 && <p className="text-sm text-muted-foreground">No quarantine locations yet.</p>}
    </div>
  )
}
