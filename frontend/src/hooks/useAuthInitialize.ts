import { useEffect } from "react"
import { useAuthStore } from "@/app/store/authStore"
import { apiClient } from "@/services/api-client"

/**
 * Hook to validate token on app initialization
 * Clears auth state if token is invalid or expired
 * This ensures users are logged out when backend session is lost
 */
export function useAuthInitialize() {
  const { token, logout, isAuthenticated } = useAuthStore()

  useEffect(() => {
    const validateToken = async () => {
      // Only validate if user appears to be authenticated
      if (!isAuthenticated || !token) {
        return
      }

      try {
        // Try to validate token by making a simple authenticated request
        // This endpoint should be lightweight and always available for authenticated users
        await apiClient.get("/auth/me")
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
  }, [token, isAuthenticated, logout])
}
