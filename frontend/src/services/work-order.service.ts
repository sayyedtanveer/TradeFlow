import apiClient from './api-client';

export interface WorkOrderSummary {
  id: string;
  wo_number: string;
  product_id: string;
  bom_id: string;
  status: 'PLANNED' | 'RELEASED' | 'IN_PROGRESS' | 'COMPLETED' | 'CLOSED';
  priority: 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT';
  planned_quantity: number;
  produced_quantity: number;
  scrap_quantity: number;
  start_date: string;
  due_date: string;
  created_at: string;
}

export interface WorkOrderMaterial {
  id: string;
  material_id: string;
  unit_id: string;
  required_quantity: number;
  issued_quantity: number;
}

export interface JobCard {
  id: string;
  operation_id: string;
  sequence: number;
  status: 'PENDING' | 'IN_PROGRESS' | 'DONE';
  assigned_to: string | null;
  started_at: string | null;
  completed_at: string | null;
  remarks: string | null;
}

export interface WorkOrderDetail extends WorkOrderSummary {
  notes: string | null;
  sales_order_id: string | null;
  materials: WorkOrderMaterial[];
  job_cards: JobCard[];
}

export interface CreateWorkOrderPayload {
  product_id: string;
  bom_id: string;
  planned_quantity: number;
  start_date: string;
  due_date: string;
  priority?: 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT';
  sales_order_id?: string;
  notes?: string;
}

export interface IssueMaterialPayload {
  material_id: string;
  quantity: number;
  unit_id: string;
}

export interface RecordProductionPayload {
  produced_quantity: number;
  scrap_quantity?: number;
  notes?: string;
}

const BASE = '/work-orders';

const workOrderService = {
  list: (params?: { status?: string; product_id?: string }) =>
    apiClient.get<WorkOrderSummary[]>(BASE, { params }),

  get: (id: string) =>
    apiClient.get<WorkOrderDetail>(`${BASE}/${id}`),

  create: (data: CreateWorkOrderPayload) =>
    apiClient.post<{ id: string }>(BASE, data),

  release: (id: string) =>
    apiClient.post<{ status: string }>(`${BASE}/${id}/release`, {}),

  start: (id: string) =>
    apiClient.post<{ status: string }>(`${BASE}/${id}/start`, {}),

  complete: (id: string) =>
    apiClient.post<{ status: string }>(`${BASE}/${id}/complete`, {}),

  close: (id: string) =>
    apiClient.post<{ status: string }>(`${BASE}/${id}/close`, {}),

  issueMaterial: (woId: string, data: IssueMaterialPayload) =>
    apiClient.post<{ message: string }>(`${BASE}/${woId}/issue-materials`, data),

  recordProduction: (woId: string, data: RecordProductionPayload) =>
    apiClient.post<{ message: string }>(`${BASE}/${woId}/record-production`, data),

  listJobCards: (woId: string) =>
    apiClient.get<JobCard[]>(`${BASE}/${woId}/job-cards`),

  startJobCard: (woId: string, jcId: string, assignedTo?: string) =>
    apiClient.patch<{ status: string }>(
      `${BASE}/${woId}/job-cards/${jcId}/start`,
      { assigned_to: assignedTo ?? null }
    ),

  completeJobCard: (woId: string, jcId: string, remarks?: string) =>
    apiClient.patch<{ status: string }>(
      `${BASE}/${woId}/job-cards/${jcId}/complete`,
      { remarks: remarks ?? null }
    ),
};

export default workOrderService;
