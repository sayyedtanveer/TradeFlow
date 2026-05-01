import { apiClient } from "./api-client"

export type RbacRole = {
  id: string
  tenant_id: string
  name: string
  label: string
  description?: string | null
  is_system: boolean
  is_active: boolean
  permissions: string[]
  permission_count: number
}

export type RbacRoleList = {
  roles: Record<string, RbacRole>
  items: RbacRole[]
  total_roles: number
}

export const rbacService = {
  async listRoles(): Promise<RbacRoleList> {
    const { data } = await apiClient.get<RbacRoleList>("/admin/rbac/roles")
    return data
  },

  async listPermissions(): Promise<{ permissions: string[]; total_permissions: number }> {
    const { data } = await apiClient.get<{ permissions: string[]; total_permissions: number }>(
      "/admin/rbac/permissions"
    )
    return data
  },

  async createRole(payload: {
    name: string
    label?: string | null
    description?: string | null
    permissions: string[]
  }): Promise<RbacRole> {
    const { data } = await apiClient.post<RbacRole>("/admin/rbac/roles", payload)
    return data
  },

  async updateRolePermissions(roleName: string, permissions: string[]): Promise<RbacRole> {
    const { data } = await apiClient.put<RbacRole>(`/admin/rbac/roles/${roleName}/permissions`, {
      permissions,
    })
    return data
  },
}
