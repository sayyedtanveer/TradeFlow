import { User } from "@/types/auth.types"
import { apiClient } from "./api-client"

const BASE = ""

type UserMutationPayload = {
  email: string
  first_name: string
  last_name: string
  role: string
  is_active?: boolean
  supplier_id?: string | null
  client_id?: string | null
}

export type CreatedUser = User & {
  temporary_password?: string
}

export type TemporaryPasswordResponse = User & {
  temporary_password: string
}

export const usersService = {
  async getUsers(filters?: { search?: string; role?: string; status?: string }): Promise<User[]> {
    const { data } = await apiClient.get<User[]>(`${BASE}/users`, { params: filters })
    return data
  },

  async getUser(id: string): Promise<User> {
    const { data } = await apiClient.get<User>(`${BASE}/users/${id}`)
    return data
  },

  async createUser(payload: UserMutationPayload): Promise<CreatedUser> {
    const { data } = await apiClient.post<CreatedUser>(`${BASE}/users`, payload)
    return data
  },

  async updateUser(id: string, payload: Partial<{
    first_name: string
    last_name: string
    role: string
    is_active: boolean
    supplier_id: string | null
    client_id: string | null
  }>): Promise<User> {
    const { data } = await apiClient.put<User>(`${BASE}/users/${id}`, payload)
    return data
  },

  async resetTemporaryPassword(id: string): Promise<TemporaryPasswordResponse> {
    const { data } = await apiClient.post<TemporaryPasswordResponse>(`${BASE}/users/${id}/temporary-password`)
    return data
  }
}
