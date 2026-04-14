import axios, { AxiosError } from "axios"
import { useAuthStore } from "@/app/store/authStore"

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: {
    "Content-Type": "application/json",
  },
})

/**
 * Extract user-friendly error message from API response
 * Handles Pydantic validation errors, standard error responses, etc.
 */
function extractErrorMessage(error: AxiosError<any>): string {
  if (!error.response) {
    return error.message || "Network error. Please check your connection."
  }

  const data = error.response.data

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

// Request interceptor: attach token
apiClient.interceptors.request.use(
  (config) => {
    const { token } = useAuthStore.getState()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor: handle errors and authentication
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Handle 401 Unauthorized - token expired or invalid
    if (error.response?.status === 401) {
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
    
    console.error("API Error:", {
      status: error.response?.status,
      message: errorMessage,
      data: error.response?.data,
      url: error.config?.url,
    })

    // Create a new error with user-friendly message
    const enhancedError = new Error(errorMessage) as AxiosError
    Object.assign(enhancedError, error)
    
    return Promise.reject(enhancedError)
  }
)
