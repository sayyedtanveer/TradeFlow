import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus, Pencil, Trash2, Search, Clock, Wrench } from "lucide-react"
import { operationsService } from "@/services/operations.service"
import { usePermissions } from "@/hooks/usePermissions"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { PageHeader } from "@/components/layout/PageHeader"
import { toast } from "sonner"

export default function OperationsListPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { hasRole } = usePermissions()
  const canEdit = hasRole(["ADMIN", "MANAGER"])

  const [search, setSearch] = useState("")

  const { data: operations = [], isLoading } = useQuery({
    queryKey: ["operations"],
    queryFn: operationsService.listOperations,
    staleTime: 30_000,
  })

  const { data: workstations = [] } = useQuery({
    queryKey: ["workstations"],
    queryFn: operationsService.listWorkstations,
    staleTime: 60_000,
  })

  const wsMap = Object.fromEntries(workstations.map((w) => [w.id, w.name]))

  const deleteMutation = useMutation({
    mutationFn: (id: string) => operationsService.deleteOperation(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["operations"] })
      toast.success("Operation deleted")
    },
    onError: () => toast.error("Failed to delete operation"),
  })

  const handleDelete = (id: string, name: string) => {
    if (window.confirm(`Delete operation "${name}"? This action cannot be undone.`)) {
      deleteMutation.mutate(id)
    }
  }

  const filtered = operations.filter((op) =>
    op.name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="w-full space-y-6">
      <PageHeader
        title="Operations"
        description="Manage the global manufacturing operations catalog."
        action={
          canEdit ? (
            <Button onClick={() => navigate("/operations/new")}>
              <Plus className="w-4 h-4 mr-2" />
              New Operation
            </Button>
          ) : undefined
        }
      />

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          placeholder="Search operations..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="py-16 text-center text-muted-foreground">Loading operations...</div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center border border-dashed rounded-xl">
          <Wrench className="w-10 h-10 text-muted-foreground mb-3" />
          <p className="text-lg font-medium">No operations found</p>
          <p className="text-sm text-muted-foreground mb-4">
            {search ? "Try a different search." : "Create your first operation to get started."}
          </p>
          {canEdit && !search && (
            <Button onClick={() => navigate("/operations/new")}>
              <Plus className="w-4 h-4 mr-2" />
              New Operation
            </Button>
          )}
        </div>
      ) : (
        <div className="rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 border-b">
              <tr className="text-left">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Workstation</th>
                <th className="px-4 py-3 font-medium text-right">Setup (min)</th>
                <th className="px-4 py-3 font-medium text-right">Run Time (min/unit)</th>
                {canEdit && <th className="px-4 py-3 font-medium text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.map((op) => (
                <tr key={op.id} className="hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-3">
                    <div className="font-medium">{op.name}</div>
                    {op.description && (
                      <div className="text-xs text-muted-foreground mt-0.5 truncate max-w-xs">
                        {op.description}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {op.workstation_id ? (
                      <Badge variant="secondary" className="font-normal">
                        {wsMap[op.workstation_id] ?? op.workstation_id.slice(0, 8)}
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground text-xs">Unassigned</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="flex items-center justify-end gap-1">
                      <Clock className="w-3.5 h-3.5 text-muted-foreground" />
                      {op.setup_time}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="flex items-center justify-end gap-1">
                      <Clock className="w-3.5 h-3.5 text-muted-foreground" />
                      {op.run_time}
                    </span>
                  </td>
                  {canEdit && (
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => navigate(`/operations/${op.id}/edit`)}
                        >
                          <Pencil className="w-3.5 h-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 hover:text-destructive"
                          onClick={() => handleDelete(op.id, op.name)}
                          disabled={deleteMutation.isPending}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
