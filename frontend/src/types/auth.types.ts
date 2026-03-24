export enum UserRole {
  ADMIN = "ADMIN",
  MANAGER = "MANAGER",
  OPERATOR = "OPERATOR",
  VIEWER = "VIEWER"
}

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  role: UserRole | string
  tenant_id?: string
  is_active: boolean
  created_at?: string
}

export interface Tenant {
  id: string
  name: string
  slug: string
  plan: string
  is_active: boolean
}

export interface AuthResponse {
  access_token: string
  token_type: string
  tenant_id: string
}

export interface MeResponse {
  user: User
  tenant: Tenant
  permissions: string[]
}
