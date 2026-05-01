import { create } from "zustand"
import { persist } from "zustand/middleware"

interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  role: string
  tenant_id?: string | null
  supplier_id?: string | null
  client_id?: string | null
  is_active: boolean
}

interface AuthState {
  token: string | null
  user: User | null
  tenant_id: string | null
  supplier_id: string | null
  client_id: string | null
  permissions: string[]
  isAuthenticated: boolean
  setAuth: (token: string, tenant_id: string) => void
  setUser: (user: User) => void
  setPermissions: (permissions: string[]) => void
  setSupplierAndClient: (supplier_id: string | null, client_id: string | null) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      tenant_id: null,
      supplier_id: null,
      client_id: null,
      permissions: [],
      isAuthenticated: false,
      setAuth: (token, tenant_id) =>
        set({ token, tenant_id, isAuthenticated: true }),
      setUser: (user) =>
        set((state) => ({
          user,
          tenant_id: user.tenant_id ?? state.tenant_id,
          supplier_id: user.supplier_id ?? null,
          client_id: user.client_id ?? null,
        })),
      setPermissions: (permissions) => set({ permissions }),
      setSupplierAndClient: (supplier_id, client_id) =>
        set({ supplier_id, client_id }),
      logout: () => set({
        token: null,
        user: null,
        tenant_id: null,
        supplier_id: null,
        client_id: null,
        permissions: [],
        isAuthenticated: false,
      }),
    }),
    {
      name: "auth-storage", // stores in localStorage
    }
  )
)
