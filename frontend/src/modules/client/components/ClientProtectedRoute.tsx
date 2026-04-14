import { Navigate, Outlet } from "react-router-dom"
import { useAuthStore } from "@/app/store/authStore"
import { normalizeRole } from "@/lib/roles.config"

export default function ClientProtectedRoute() {
  const { isAuthenticated, user } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/client/login" replace />
  }

  if (!user || normalizeRole(user.role) !== "CLIENT") {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}
