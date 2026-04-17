import { useCallback } from "react"
import { AxiosError } from "axios"
import { useToast } from "./use-toast"
import { extractErrorMessage } from "@/services/api-client"

/**
 * Hook for handling API errors with automatic toast notifications
 * Use this to automatically show validation errors and API errors as toasts
 */
export function useApiError() {
  const { toast } = useToast()

  const handleError = useCallback((
    error: unknown,
    options?: {
      title?: string
      showToast?: boolean
    }
  ) => {
    const isAxiosError = error instanceof AxiosError
    const errorMessage = isAxiosError ? extractErrorMessage(error) : (error instanceof Error ? error.message : "An error occurred")

    if (options?.showToast !== false) {
      toast({
        title: options?.title || "Error",
        description: errorMessage,
        variant: "destructive",
      })
    }

    console.error("API Error:", error)
    return errorMessage
  }, [toast])

  return { handleError }
}

/**
 * Extract structured validation errors from axios error
 * Useful for displaying field-level validation errors
 */
export function extractValidationErrors(error: AxiosError<any>): Record<string, string[]> {
  const errors: Record<string, string[]> = {}
  
  if (!error.response?.data) return errors
  
  const data = error.response.data
  
  // Handle Pydantic validation errors (422)
  if (error.response.status === 422 && Array.isArray(data)) {
    data.forEach((err) => {
      const field = Array.isArray(err.loc) ? err.loc[err.loc.length - 1] : 'general'
      if (!errors[field]) {
        errors[field] = []
      }
      errors[field].push(err.msg)
    })
  }
  
  return errors
}
