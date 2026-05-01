import { apiClient } from "./api-client"

const BASE = ""

export type AuditLogItem = {
  id: string
  tenant_id?: string | null
  user_id?: string | null
  actor: {
    email?: string | null
    name?: string | null
  }
  action: string
  entity_type?: string | null
  entity_id?: string | null
  summary?: string | null
  business_step?: string | null
  module?: string | null
  document_no?: string | null
  source?: string | null
  status_code?: number | null
  before_value?: Record<string, unknown> | null
  after_value?: Record<string, unknown> | null
  ip_address?: string | null
  correlation_id?: string | null
  extra?: Record<string, unknown> | null
  occurred_at: string
}

export type AuditLogResponse = {
  total: number
  skip: number
  limit: number
  items: AuditLogItem[]
}

export const auditService = {
  async getAuditLogs(params?: {
    action?: string
    entity_type?: string
    entity_id?: string
    search?: string
    skip?: number
    limit?: number
  }): Promise<AuditLogResponse> {
    const { data } = await apiClient.get<AuditLogResponse>(`${BASE}/audit-logs`, { params })
    return data
  },
}
