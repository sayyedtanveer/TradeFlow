import { useMemo, useState, type Dispatch, type SetStateAction } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { rbacService, type RbacRole } from "@/services/rbac.service"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useToast } from "@/hooks/use-toast"

function permissionMatches(permission: string, search: string) {
  return permission.toLowerCase().includes(search.trim().toLowerCase())
}

export function RoleManagementPanel() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const [name, setName] = useState("")
  const [label, setLabel] = useState("")
  const [permissionSearch, setPermissionSearch] = useState("")
  const [selectedPermissions, setSelectedPermissions] = useState<Set<string>>(new Set())
  const [editingRole, setEditingRole] = useState<RbacRole | null>(null)
  const [editingPermissions, setEditingPermissions] = useState<Set<string>>(new Set())

  const rolesQuery = useQuery({
    queryKey: ["rbac", "roles"],
    queryFn: rbacService.listRoles,
  })

  const permissionsQuery = useQuery({
    queryKey: ["rbac", "permissions"],
    queryFn: rbacService.listPermissions,
  })

  const permissions = permissionsQuery.data?.permissions ?? []
  const filteredPermissions = useMemo(
    () => permissions.filter((permission) => permissionMatches(permission, permissionSearch)),
    [permissions, permissionSearch]
  )

  const createRoleMutation = useMutation({
    mutationFn: () =>
      rbacService.createRole({
        name,
        label: label || null,
        permissions: Array.from(selectedPermissions).sort(),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rbac", "roles"] })
      setName("")
      setLabel("")
      setSelectedPermissions(new Set())
      toast({ title: "Role created", description: "The role is now available when creating users." })
    },
    onError: (error: any) => {
      toast({
        title: "Role creation failed",
        description: error?.response?.data?.detail || error?.message || "Unable to create role",
        variant: "destructive",
      })
    },
  })

  const updatePermissionsMutation = useMutation({
    mutationFn: () =>
      rbacService.updateRolePermissions(editingRole!.name, Array.from(editingPermissions).sort()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rbac", "roles"] })
      setEditingRole(null)
      setEditingPermissions(new Set())
      toast({ title: "Permissions updated" })
    },
    onError: (error: any) => {
      toast({
        title: "Permission update failed",
        description: error?.response?.data?.detail || error?.message || "Unable to update permissions",
        variant: "destructive",
      })
    },
  })

  const togglePermission = (
    permission: string,
    setter: Dispatch<SetStateAction<Set<string>>>
  ) => {
    setter((current) => {
      const next = new Set(current)
      if (next.has(permission)) {
        next.delete(permission)
      } else {
        next.add(permission)
      }
      return next
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Role & Permission Management</CardTitle>
        <CardDescription>
          Admin-managed roles are tenant-scoped. Assign permissions here, then select the role when inviting users.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-4 rounded-lg border bg-muted/20 p-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="role-name">Role name</Label>
              <Input
                id="role-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="production_supervisor"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="role-label">Label</Label>
              <Input
                id="role-label"
                value={label}
                onChange={(event) => setLabel(event.target.value)}
                placeholder="Production Supervisor"
              />
            </div>
          </div>

          <PermissionPicker
            permissions={filteredPermissions}
            selected={selectedPermissions}
            search={permissionSearch}
            onSearch={setPermissionSearch}
            onToggle={(permission) => togglePermission(permission, setSelectedPermissions)}
          />

          <Button
            onClick={() => createRoleMutation.mutate()}
            disabled={!name.trim() || selectedPermissions.size === 0 || createRoleMutation.isPending}
          >
            {createRoleMutation.isPending ? "Creating..." : "Create Role"}
          </Button>
        </div>

        <div className="space-y-3">
          {rolesQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading roles...</p>
          ) : (
            rolesQuery.data?.items.map((role) => (
              <div key={role.name} className="rounded-lg border p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-medium">{role.label}</p>
                      {role.is_system && <Badge variant="secondary">System</Badge>}
                    </div>
                    <p className="text-xs text-muted-foreground">{role.name}</p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setEditingRole(role)
                      setEditingPermissions(new Set(role.permissions))
                    }}
                  >
                    Edit Permissions
                  </Button>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {role.permissions.slice(0, 8).map((permission) => (
                    <Badge key={permission} variant="outline">
                      {permission}
                    </Badge>
                  ))}
                  {role.permissions.length > 8 && (
                    <Badge variant="secondary">+{role.permissions.length - 8} more</Badge>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {editingRole && (
          <div className="lg:col-span-2 rounded-lg border bg-background p-4">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-medium">Editing {editingRole.label}</p>
                <p className="text-xs text-muted-foreground">{editingRole.name}</p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setEditingRole(null)}>
                  Cancel
                </Button>
                <Button
                  onClick={() => updatePermissionsMutation.mutate()}
                  disabled={editingPermissions.size === 0 || updatePermissionsMutation.isPending}
                >
                  {updatePermissionsMutation.isPending ? "Saving..." : "Save Permissions"}
                </Button>
              </div>
            </div>
            <PermissionPicker
              permissions={filteredPermissions}
              selected={editingPermissions}
              search={permissionSearch}
              onSearch={setPermissionSearch}
              onToggle={(permission) => togglePermission(permission, setEditingPermissions)}
            />
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function PermissionPicker({
  permissions,
  selected,
  search,
  onSearch,
  onToggle,
}: {
  permissions: string[]
  selected: Set<string>
  search: string
  onSearch: (value: string) => void
  onToggle: (permission: string) => void
}) {
  return (
    <div className="space-y-3">
      <Input
        value={search}
        onChange={(event) => onSearch(event.target.value)}
        placeholder="Search permissions, e.g. sales or inventory"
      />
      <div className="grid max-h-56 gap-2 overflow-auto rounded-md border bg-background p-3 sm:grid-cols-2">
        {permissions.map((permission) => (
          <label key={permission} className="flex cursor-pointer items-center gap-2 text-sm">
            <Checkbox checked={selected.has(permission)} onCheckedChange={() => onToggle(permission)} />
            <span>{permission}</span>
          </label>
        ))}
      </div>
    </div>
  )
}
