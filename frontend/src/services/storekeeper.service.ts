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

const BASE = '/storekeeper';

export const storekeeperService = {
  getIssueQueue: () => apiClient.get<IssueQueueItem[]>(`${BASE}/issue-queue`),
  getShortageQueue: () => apiClient.get<ShortageQueueItem[]>(`${BASE}/shortage-queue`),
  getPartiallyIssued: () => apiClient.get(`${BASE}/partially-issued-wo`),
  getPendingReservations: () => apiClient.get<PendingReservationItem[]>(`${BASE}/pending-reservations`),
  getPendingReturns: () => apiClient.get(`${BASE}/pending-returns`),
  getInventoryAlerts: () => apiClient.get(`${BASE}/inventory-alerts`),
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
