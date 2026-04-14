import { create } from "zustand"
import { persist } from "zustand/middleware"

interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  role: string
  client_id?: string | null
  supplier_id?: string | null
  tenant_id?: string | null
}

interface AuthState {
  token: string | null
  user: User | null
  tenant_id: string | null
  isAuthenticated: boolean
  setAuth: (token: string, tenant_id: string) => void
  setUser: (user: User) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      tenant_id: null,
      isAuthenticated: false,
      setAuth: (token, tenant_id) =>
        set({ token, tenant_id, isAuthenticated: true }),
      setUser: (user) => set({ user }),
      logout: () => set({ token: null, user: null, tenant_id: null, isAuthenticated: false }),
    }),
    {
      name: "auth-storage", // stores in localStorage
    }
  )
)
