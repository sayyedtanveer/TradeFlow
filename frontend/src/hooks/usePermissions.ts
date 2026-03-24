import { useAuthStore } from "@/app/store/authStore"

/**
 * Phase 0 backend RBAC mapping:
 * ADMIN     → *
 * MANAGER   → module:read, module:write
 * OPERATOR  → module:read, module:write (restricted)
 * VIEWER    → module:read
 * 
 * In a real complex app, the backend returns the exact permissions array in /auth/me.
 * For this UI, we can do rough checks based on the `user.role` to hide/show buttons.
 */
export function usePermissions() {
  const { user } = useAuthStore()

  const hasRole = (roles: string[]) => {
    if (!user) return false
    return roles.includes(user.role)
  }

  const isAdmin = () => hasRole(["ADMIN"])
  const canWriteInventory = () => hasRole(["ADMIN", "MANAGER", "OPERATOR"])
  const canDeleteInventory = () => hasRole(["ADMIN", "MANAGER"])

  return {
    hasRole,
    isAdmin,
    canWriteInventory,
    canDeleteInventory,
    role: user?.role,
  }
}
