import { Navigate, Outlet, useLocation } from "react-router-dom"
import { useEffect, useState } from "react"
import { useAuthStore } from "@/app/store/authStore"
import { isClientSession } from "@/lib/auth-session"
import { normalizeRole } from "@/lib/roles.config"
import { apiClient } from "@/services/api-client"

interface ProtectedRouteProps {
  allowedRoles?: string[]
  roles?: string[]
  children?: React.ReactNode
}

export function ProtectedRoute({ allowedRoles, roles, children }: ProtectedRouteProps) {
  const { isAuthenticated, user, logout, token, client_id } = useAuthStore()
  const location = useLocation()
  const [isValidating, setIsValidating] = useState(true)
  const [isValid, setIsValid] = useState(false)

  // Support both prop names
  const effectiveRoles = roles || allowedRoles

  // Validate token when entering protected route
  useEffect(() => {
    const validateToken = async () => {
      if (!isAuthenticated || !token) {
        setIsValid(false)
        setIsValidating(false)
        return
      }

      try {
        const validationEndpoint = isClientSession({
          token,
          userRole: user?.role,
          clientId: client_id,
          pathname: location.pathname,
        })
          ? "/client/profile"
          : "/auth/me"
        await apiClient.get(validationEndpoint)
        setIsValid(true)
      } catch (error) {
        // Token is invalid, expired, or user session was lost
        logout()
        setIsValid(false)
      } finally {
        setIsValidating(false)
      }
    }

    validateToken()
  }, [isAuthenticated, token, logout, user?.role, client_id, location.pathname])

  // Show loading state while validating
  if (isValidating) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>
  }

  // Not logged in or token validation failed, redirect to login page
  if (!isValid || !isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (!effectiveRoles && user) {
    const normalizedUserRole = normalizeRole(user.role)
    const roleHome =
      normalizedUserRole === "CLIENT"
        ? "/client"
        : normalizedUserRole === "SUPPLIER"
        ? "/supplier-portal"
        : null

    if (
      roleHome &&
      location.pathname !== roleHome &&
      !location.pathname.startsWith(`${roleHome}/`)
    ) {
      return <Navigate to={roleHome} replace />
    }
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
