import { User, UserRole } from "@/types/auth.types"

// Temporary mock frontend behavior
export const mockUsers: User[] = [
  { id: "1", email: "admin@acme.com", first_name: "Admin", last_name: "User", role: UserRole.ADMIN, tenant_id: "tenant-1", is_active: true, created_at: new Date().toISOString() },
  { id: "2", email: "manager@acme.com", first_name: "John", last_name: "Manager", role: UserRole.MANAGER, tenant_id: "tenant-1", is_active: true, created_at: new Date().toISOString() },
  { id: "3", email: "operator@acme.com", first_name: "Bob", last_name: "Storekeeper", role: UserRole.OPERATOR, tenant_id: "tenant-1", is_active: true, created_at: new Date().toISOString() },
  { id: "4", email: "viewer@acme.com", first_name: "Alice", last_name: "Observer", role: UserRole.VIEWER, tenant_id: "tenant-1", is_active: false, created_at: new Date().toISOString() },
]

export const usersService = {
  async getUsers(filters?: { search?: string; role?: string; status?: string }): Promise<User[]> {
    await new Promise(resolve => setTimeout(resolve, 500))
    let result = [...mockUsers]

    if (filters?.search) {
      const search = filters.search.toLowerCase()
      result = result.filter(u => 
        u.email.toLowerCase().includes(search) || 
        `${u.first_name} ${u.last_name}`.toLowerCase().includes(search)
      )
    }

    if (filters?.role) {
      result = result.filter(u => u.role === filters.role)
    }

    if (filters?.status) {
      const isActive = filters.status === "active"
      result = result.filter(u => u.is_active === isActive)
    }

    return result
  },

  async getUser(id: string): Promise<User> {
    await new Promise(resolve => setTimeout(resolve, 300))
    const user = mockUsers.find(u => u.id === id)
    if (!user) throw new Error("User not found")
    return user
  },

  async createUser(data: Partial<User>): Promise<User> {
    await new Promise(resolve => setTimeout(resolve, 600))
    return { id: Math.random().toString(), ...data } as User
  },

  async updateUser(id: string, data: Partial<User>): Promise<User> {
    await new Promise(resolve => setTimeout(resolve, 600))
    const user = mockUsers.find(u => u.id === id)
    return { ...user, ...data } as User
  }
}
