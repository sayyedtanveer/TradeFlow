import { useAuthStore } from "@/app/store/authStore"
import { UserRole, normalizeRole } from "@/lib/roles.config"

/**
 * Hook for permission checking
 * Uses centralized role configuration from roles.config.ts
 */
export function usePermissions() {
  const { user } = useAuthStore()

  const hasRole = (roles: (UserRole | string)[]): boolean => {
    if (!user) return false
    const normalized = normalizeRole(user.role)
    return roles.some(role => 
      normalizeRole(role as string) === normalized
    )
  }

  const isAdmin = (): boolean => hasRole([UserRole.ADMIN])
  const isManager = (): boolean => hasRole([UserRole.MANAGER])
  const isOperator = (): boolean => hasRole([UserRole.OPERATOR])
  const isViewer = (): boolean => hasRole([UserRole.VIEWER])
  
  const canWrite = (): boolean => hasRole([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR])
  const canDelete = (): boolean => hasRole([UserRole.ADMIN, UserRole.MANAGER])
  const canEditBOM = (): boolean => hasRole([UserRole.ADMIN, UserRole.MANAGER])
  const canViewBOM = (): boolean => !!user

  return {
    hasRole,
    isAdmin,
    isManager,
    isOperator,
    isViewer,
    canWrite,
    canDelete,
    canEditBOM,
    canViewBOM,
    role: user?.role,
  }
}
