import { create } from "zustand"
import { persist } from "zustand/middleware"

interface UIState {
  isSidebarOpen: boolean
  theme: "light" | "dark" | "system"
  pendingSyncCount: number
  toggleSidebar: () => void
  setSidebarOpen: (isOpen: boolean) => void
  setTheme: (theme: "light" | "dark" | "system") => void
  incrementSyncQueue: () => void
  clearSyncQueue: () => void
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      isSidebarOpen: typeof window === "undefined" ? true : window.innerWidth >= 768,
      theme: "system",
      pendingSyncCount: 0,
      toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
      setSidebarOpen: (isOpen) => set({ isSidebarOpen: isOpen }),
      setTheme: (theme) => set({ theme }),
      incrementSyncQueue: () => set((state) => ({ pendingSyncCount: state.pendingSyncCount + 1 })),
      clearSyncQueue: () => set({ pendingSyncCount: 0 }),
    }),
    {
      name: "ui-storage",
      partialize: (state) => ({ theme: state.theme }), // Only persist theme, not sidebar state or sync count
    }
  )
)
