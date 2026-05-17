import { apiClient } from './api-client';

export interface IssueQueueItem {
  work_order_id: string;
  wo_number: string;
  material_id: string;
  material_code?: string | null;
  material_name?: string | null;
  batch_id?: string | null;
  batch_number?: string | null;
  required_quantity: number;
  reserved_quantity?: number;
  issued_quantity: number;
  consumed_quantity?: number;
  returned_quantity?: number;
  remaining_quantity: number;
  available_quantity?: number | null;
  due_date?: string;
  status: string;
}

export interface ShortageQueueItem {
  shortage_id: string;
  work_order_id: string;
  wo_number?: string | null;
  material_id: string;
  material_code?: string | null;
  material_name?: string | null;
  shortage_quantity: number;
  status: string;
}

export interface PendingReservationItem {
  reservation_id: string;
  work_order_id: string;
  wo_number: string;
  material_id: string;
  material_code: string;
  material_name: string;
  batch_id?: string | null;
  batch_number?: string | null;
  reserved_quantity: number;
  issued_quantity: number;
  pending_quantity: number;
  status: string;
}

export interface PendingReturnItem {
  reservation_id: string;
  work_order_id: string;
  wo_number: string;
  material_id: string;
  material_code: string;
  material_name: string;
  batch_id?: string | null;
  batch_number?: string | null;
  issued_quantity: number;
  consumed_quantity: number;
  returned_quantity: number;
  returnable_quantity: number;
  status: string;
}

export interface InventoryAlertItem {
  alert_type: string;
  severity: string;
  material_id: string;
  material_code: string;
  material_name: string;
  batch_id?: string | null;
  batch_number?: string | null;
  current_stock?: number | null;
  reorder_level?: number | null;
  remaining_quantity?: number | null;
  message: string;
}

export interface OperationalBatchItem {
  batch_id: string;
  batch_number: string;
  material_id: string;
  material_code: string;
  material_name: string;
  original_quantity: number;
  remaining_quantity: number;
  reserved_quantity: number;
  consumed_quantity: number;
  returned_quantity: number;
  location_id?: string | null;
  location_name?: string | null;
  location_type?: string | null;
  expiry_date?: string | null;
  status: string;
  is_blocked: boolean;
  is_near_empty: boolean;
}

const BASE = '/storekeeper';

export const storekeeperService = {
  getIssueQueue: () => apiClient.get<IssueQueueItem[]>(`${BASE}/issue-queue`),
  getShortageQueue: () => apiClient.get<ShortageQueueItem[]>(`${BASE}/shortage-queue`),
  getPartiallyIssued: () => apiClient.get(`${BASE}/partially-issued-wo`),
  getPendingReservations: () => apiClient.get<PendingReservationItem[]>(`${BASE}/pending-reservations`),
  getPendingReturns: () => apiClient.get<PendingReturnItem[]>(`${BASE}/pending-returns`),
  getInventoryAlerts: () => apiClient.get<InventoryAlertItem[]>(`${BASE}/inventory-alerts`),
  getOperationalBatches: () => apiClient.get<OperationalBatchItem[]>(`${BASE}/operational-batches`),
  searchTraceability: (q: string) => apiClient.get(`${BASE}/traceability/search`, { params: { q } }),
  issueMaterial: (data: {
    work_order_id: string;
    material_id: string;
    quantity: number;
    unit_id?: string | null;
    batch_id?: string | null;
  }) => apiClient.post(`${BASE}/issue-material`, data),
  partialIssue: (data: {
    work_order_id: string;
    material_id: string;
    quantity: number;
    unit_id?: string | null;
    batch_id?: string | null;
  }) => apiClient.post(`${BASE}/partial-issue`, data),
  returnMaterial: (data: {
    work_order_id: string;
    material_id: string;
    quantity: number;
    unit_id?: string | null;
    batch_id?: string | null;
  }) => apiClient.post(`${BASE}/return-material`, data),
};

export default storekeeperService;
