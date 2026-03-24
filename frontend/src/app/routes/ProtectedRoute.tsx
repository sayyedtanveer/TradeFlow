import { Navigate, Outlet } from "react-router-dom"
import { useAuthStore } from "@/app/store/authStore"

interface ProtectedRouteProps {
  allowedRoles?: string[]
}

export function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuthStore()

  if (!isAuthenticated) {
    // Not logged in, redirect to login page
    return <Navigate to="/login" replace />
  }

  if (allowedRoles && allowedRoles.length > 0 && user) {
    if (!allowedRoles.includes(user.role)) {
      // Role not allowed, redirect to generic dashboard/unauthorized
      // In a real app you might show a dedicated 403 page
      return <Navigate to="/" replace />
    }
  }

  return <Outlet />
}
