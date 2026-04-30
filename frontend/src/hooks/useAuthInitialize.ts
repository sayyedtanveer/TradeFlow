import { useEffect } from "react"
import { useAuthStore } from "@/app/store/authStore"
import { isClientSession } from "@/lib/auth-session"
import { apiClient } from "@/services/api-client"

/**
 * Hook to validate token on app initialization
 * Clears auth state if token is invalid or expired
 * This ensures users are logged out when backend session is lost
 */
export function useAuthInitialize() {
  const { token, logout, isAuthenticated, user, client_id } = useAuthStore()

  useEffect(() => {
    const validateToken = async () => {
      // Only validate if user appears to be authenticated
      if (!isAuthenticated || !token) {
        return
      }

      try {
        const validationEndpoint = isClientSession({
          token,
          userRole: user?.role,
          clientId: client_id,
        })
          ? "/client/profile"
          : "/auth/me"
        await apiClient.get(validationEndpoint)
      } catch (error) {
        // If token validation fails, user is not actually authenticated
        // This handles cases where:
        // 1. Token is expired
        // 2. Backend was restarted and token is invalid
        // 3. User was deleted or deactivated
        logout()
      }
    }

    validateToken()
  }, [token, isAuthenticated, logout, user?.role, client_id])
}
