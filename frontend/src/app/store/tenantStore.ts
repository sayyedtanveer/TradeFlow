import { create } from "zustand"

interface TenantStore {
  name: string | null
  slug: string | null
  plan: string | null
  setTenantInfo: (name: string, slug: string, plan: string) => void
  clearTenant: () => void
}

export const useTenantStore = create<TenantStore>((set) => ({
  name: null,
  slug: null,
  plan: null,
  setTenantInfo: (name, slug, plan) => set({ name, slug, plan }),
  clearTenant: () => set({ name: null, slug: null, plan: null }),
}))
