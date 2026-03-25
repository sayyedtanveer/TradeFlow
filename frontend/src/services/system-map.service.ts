import { apiClient } from "./api-client"

export interface SystemModule {
  id: string
  name: string
  route: string
  status: string
  icon: string
}

export interface SystemConnection {
  source: string
  target: string
}

export interface SystemMapResponse {
  modules: SystemModule[]
  connections: SystemConnection[]
}

export const systemMapService = {
  getSystemMap: async (): Promise<SystemMapResponse> => {
    const response = await apiClient.get("/system-map")
    return response.data
  },
}
