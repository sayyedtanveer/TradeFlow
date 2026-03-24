export interface ApiResponse<T> {
  data: T
  message?: string
  status: "success" | "error"
}

export interface PaginatedResponse<T> {
  data: T[]
  meta: {
    total: number
    page: number
    limit: number
    total_pages: number
  }
}

export interface ApiError {
  message: string
  code: string
  details?: unknown
}
