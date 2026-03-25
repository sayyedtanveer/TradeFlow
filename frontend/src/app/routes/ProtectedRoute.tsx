import { Navigate, Outlet } from "react-router-dom"
import { useAuthStore } from "@/app/store/authStore"
import { normalizeRole } from "@/lib/roles.config"

interface ProtectedRouteProps {
  allowedRoles?: string[]
  roles?: string[]
  children?: React.ReactNode
}

export function ProtectedRoute({ allowedRoles, roles, children }: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuthStore()

  // Support both prop names
  const effectiveRoles = roles || allowedRoles

  if (!isAuthenticated) {
    // Not logged in, redirect to login page
    return <Navigate to="/login" replace />
  }

  if (effectiveRoles && effectiveRoles.length > 0 && user) {
    // Normalize backend role (lowercase) to uppercase for comparison
    const normalizedUserRole = normalizeRole(user.role)
    if (!normalizedUserRole || !effectiveRoles.includes(normalizedUserRole)) {
      // Role not allowed, redirect to generic dashboard/unauthorized
      return <Navigate to="/" replace />
    }
  }

  return children ? <>{children}</> : <Outlet />
}
