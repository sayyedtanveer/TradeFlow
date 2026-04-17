import { User, UserRole } from "@/types/auth.types"
import { apiClient } from "./api-client"

const BASE = ""

export const usersService = {
  async getUsers(filters?: { search?: string; role?: string; status?: string }): Promise<User[]> {
    const { data } = await apiClient.get<User[]>(`${BASE}/users`, { params: filters })
    return data
  },

  async getUser(id: string): Promise<User> {
    const { data } = await apiClient.get<User>(`${BASE}/users/${id}`)
    return data
  },

  async createUser(payload: {
    email: string
    first_name: string
    last_name: string
    role: string
    is_active?: boolean
  }): Promise<User> {
    const { data } = await apiClient.post<User>(`${BASE}/users`, payload)
    return data
  },

  async updateUser(id: string, payload: Partial<{
    first_name: string
    last_name: string
    role: string
    is_active: boolean
  }>): Promise<User> {
    const { data } = await apiClient.put<User>(`${BASE}/users/${id}`, payload)
    return data
  }
}
