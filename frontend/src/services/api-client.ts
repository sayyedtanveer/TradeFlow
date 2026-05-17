import axios, { AxiosError } from "axios"
import { useAuthStore } from "@/app/store/authStore"

// Default to `/api/v1` when `VITE_API_URL` is not provided in development.
// This keeps calls like `/inventory/...` routed to the backend via the dev proxy.
const DEFAULT_API_BASE = import.meta.env.VITE_API_URL ?? "/api/v1"

export const apiClient = axios.create({
  baseURL: DEFAULT_API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
})

export default apiClient

const AUTH_VALIDATION_ENDPOINTS = new Set(["/auth/me", "/client/profile"])

function normalizeRequestUrl(url: string | undefined): string {
  if (!url) return ""
  try {
    const parsed = new URL(url, window.location.origin)
    return parsed.pathname.replace(/^\/api\/v1/, "")
  } catch {
    return url.replace(/^\/api\/v1/, "")
  }
}

function authFailureDetail(error: AxiosError<any>): string {
  const data = error.response?.data
  const detail = data?.detail ?? data?.message ?? data?.error?.message ?? data?.error?.code ?? ""
  return typeof detail === "string" ? detail.toLowerCase() : JSON.stringify(detail).toLowerCase()
}

export function isSessionInvalidError(error: unknown): boolean {
  if (!axios.isAxiosError(error) || error.response?.status !== 401) {
    return false
  }

  const requestPath = normalizeRequestUrl(error.config?.url)
  const detail = authFailureDetail(error)
  const tokenWasSent = Boolean(error.config?.headers?.Authorization)

  const explicitInvalid =
    detail.includes("auth_failed") ||
    detail.includes("not authenticated") ||
    detail.includes("authentication required") ||
    detail.includes("invalid or expired token") ||
    detail.includes("invalid token") ||
    detail.includes("expired token") ||
    detail.includes("bad tenant_id") ||
    detail.includes("bad user_id") ||
    detail.includes("missing tenant_id") ||
    detail.includes("missing user_id")

  // Only treat auth validation endpoints as “session invalid” enough to force logout.
  // Other 401s (e.g., permissions/tenant/account issues) must not clear the session.
  if (!AUTH_VALIDATION_ENDPOINTS.has(requestPath)) {
    return false
  }

  return explicitInvalid
}

function isAuthRequest(url: string | undefined): boolean {
  const requestPath = normalizeRequestUrl(url)
  return requestPath.startsWith("/auth/login") || requestPath.startsWith("/auth/register")
}

/**
 * Extract user-friendly error message from API response
 * Handles Pydantic validation errors, standard error responses, etc.
 */
export function extractErrorMessage(error: AxiosError<any>): string {
  if (!error.response) {
    return error.message || "Network error. Please check your connection."
  }

  const data = error.response.data

  if (data?.error?.message) {
    return typeof data.error.message === "string" ? data.error.message : JSON.stringify(data.error.message)
  }

  // Handle Pydantic validation errors (422 Unprocessable Entity)
  if (error.response.status === 422) {
    // Pydantic returns an array of validation errors
    if (Array.isArray(data)) {
      const messages = data
        .map((err) => {
          // Each error has: {type, loc, msg, input, ctx}
          if (err.msg) return err.msg
          if (err.detail) return err.detail
          return "Validation error"
        })
        .filter(Boolean)
      return messages.join(", ") || "Validation error"
    }
    // Some APIs return {detail: "..."}
    if (data.detail) return data.detail
    return "Validation error"
  }

  // Handle standard error responses {detail: "..."}
  if (data.detail) {
    return typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)
  }

  // Handle {message: "..."}
  if (data.message) {
    return typeof data.message === "string" ? data.message : JSON.stringify(data.message)
  }

  // Handle raw string errors
  if (typeof data === "string") {
    return data
  }

  // Fallback to HTTP status text
  return error.response.statusText || "An error occurred"
}

// Request interceptor: attach token and clean up params
apiClient.interceptors.request.use(
  (config) => {
    const { token, tenant_id } = useAuthStore.getState()
    
    // Always set Authorization header if token exists
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
      config.headers["Authorization"] = `Bearer ${token}`  // Redundant but explicit for FormData
    }
    
    // Add tenant ID header for multi-tenant support
    if (tenant_id) {
      config.headers["X-Tenant-ID"] = tenant_id
    }

    if (config.data instanceof FormData) {
      // For FormData, remove the default JSON content-type so browser can set proper multipart boundary
      delete config.headers["Content-Type"]
      
      // Ensure Authorization header is preserved for FormData requests
      if (token) {
        config.headers["Authorization"] = `Bearer ${token}`
      }
      
    }
    
    // Remove empty/null query parameters to prevent backend validation errors
    if (config.params) {
      Object.keys(config.params).forEach(key => {
        if (config.params[key] === null || config.params[key] === undefined || config.params[key] === '') {
          delete config.params[key]
        }
      })
    }
    
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor: handle errors and authentication
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Handle true session invalidation. Page-specific 401s should surface to
    // the screen instead of clearing the whole ERP session during navigation.
    if (isSessionInvalidError(error) && !isAuthRequest(error.config?.url)) {
      const { logout } = useAuthStore.getState()
      logout()
      const loginPath = window.location.pathname.startsWith("/client") ? "/client/login" : "/login"
      if (window.location.pathname !== loginPath) {
        window.location.href = loginPath
      }
      return Promise.reject(error)
    }

    // Extract and enhance error message for better debugging
    const errorMessage = extractErrorMessage(error)
    const tokenWasSent = Boolean(error.config?.headers?.Authorization)
    
    console.error("API Error:", {
      status: error.response?.status,
      message: errorMessage,
      url: error.config?.url,
      method: error.config?.method,
      tokenWasSent,
      data: error.response?.data,
    })

    // Create a new error with user-friendly message
    const enhancedError = new Error(errorMessage) as AxiosError
    Object.assign(enhancedError, error)
    
    return Promise.reject(enhancedError)
  }
)
