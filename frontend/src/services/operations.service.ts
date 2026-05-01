import { apiClient } from "./api-client";

export interface Operation {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  workstation_id?: string;
  setup_time: number;   // minutes
  run_time: number;     // minutes per unit
}

export interface Workstation {
  id: string;
  tenant_id: string;
  code: string;
  name: string;
  capacity_hours_per_day: number;
  hourly_rate: number;
  is_active: boolean;
}

export interface CreateOperationInput {
  name: string;
  description?: string;
  workstation_id: string;
  setup_time: number;
  run_time: number;
}

export interface UpdateOperationInput extends Partial<CreateOperationInput> {}

export const operationsService = {
  async listOperations(): Promise<Operation[]> {
    const { data } = await apiClient.get("/operations");
    return data;
  },

  async createOperation(payload: CreateOperationInput): Promise<string> {
    const { data } = await apiClient.post("/operations", payload);
    return data; // returns UUID
  },

  async updateOperation(id: string, payload: UpdateOperationInput): Promise<Operation> {
    const { data } = await apiClient.put(`/operations/${id}`, payload);
    return data;
  },

  async deleteOperation(id: string): Promise<void> {
    await apiClient.delete(`/operations/${id}`);
  },

  async listWorkstations(): Promise<Workstation[]> {
    const { data } = await apiClient.get("/workstations");
    return data;
  },
};
