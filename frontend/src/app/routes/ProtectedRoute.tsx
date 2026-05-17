import { Navigate, Outlet, useLocation } from "react-router-dom"
import { useEffect, useState } from "react"
import { useAuthStore } from "@/app/store/authStore"
import { isClientSession } from "@/lib/auth-session"
import { normalizeRole } from "@/lib/roles.config"
import { apiClient, isSessionInvalidError } from "@/services/api-client"

interface ProtectedRouteProps {
  allowedRoles?: string[]
  roles?: string[]
  children?: React.ReactNode
}

export function ProtectedRoute({ allowedRoles, roles, children }: ProtectedRouteProps) {
  const { isAuthenticated, user, logout, token, client_id, hasHydrated } = useAuthStore()
  const location = useLocation()
  const [isValidating, setIsValidating] = useState(true)
  const [isValid, setIsValid] = useState(false)

  // Support both prop names
  const effectiveRoles = roles || allowedRoles

  // Validate token when entering protected route
  useEffect(() => {
    const validateToken = async () => {
      if (!hasHydrated) {
        return
      }

      if (!isAuthenticated || !token) {
        setIsValid(false)
        setIsValidating(false)
        return
      }

      setIsValidating(true)
      try {
        const validationEndpoint = isClientSession({
          token,
          userRole: user?.role,
          clientId: client_id,
        })
          ? "/client/profile"
          : "/auth/me"
        await apiClient.get(validationEndpoint)
        setIsValid(true)
      } catch (error) {
        if (isSessionInvalidError(error)) {
          logout()
          setIsValid(false)
        } else {
          // Keep the local session intact for transient validation failures;
          // page-level queries can show their own error state.
          console.warn("Auth validation was inconclusive; preserving session.", error)
          setIsValid(true)
        }
      } finally {
        setIsValidating(false)
      }
    }

    validateToken()
  }, [hasHydrated, isAuthenticated, token, logout, user?.role, client_id])

  // Show loading state while validating
  if (!hasHydrated || isValidating) {
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
