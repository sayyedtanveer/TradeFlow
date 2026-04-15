// Re-export API client for backward compatibility
export { apiClient as default } from './api-client';
export { apiClient } from './api-client';

// Analytics API - uses the base apiClient
export const analyticsAPI = {
  getDashboard: async (type: string) => {
    const response = await (await import('./api-client')).apiClient.get(`/analytics/${type}`);
    return response.data;
  },
  getReports: async () => {
    const response = await (await import('./api-client')).apiClient.get('/analytics/reports');
    return response.data;
  },
  createReport: async (data: any) => {
    const response = await (await import('./api-client')).apiClient.post('/analytics/reports', data);
    return response.data;
  },
  listSavedReports: async () => {
    const response = await (await import('./api-client')).apiClient.get('/analytics/saved-reports');
    return response.data;
  },
  createSavedReport: async (data: any) => {
    const response = await (await import('./api-client')).apiClient.post('/analytics/saved-reports', data);
    return response.data;
  },
  generateFinanceReport: async (start: string, end: string) => {
    const response = await (await import('./api-client')).apiClient.get('/analytics/finance', { params: { start, end } });
    return response.data;
  },
  getDashboardSummary: async (start: string, end: string) => {
    const response = await (await import('./api-client')).apiClient.get(`/analytics/summary`, { params: { start, end } });
    return response.data;
  },
  generateInventoryReport: async (start: string, end: string) => {
    const response = await (await import('./api-client')).apiClient.get('/analytics/inventory', { params: { start, end } });
    return response.data;
  },
  generateProductionReport: async (start: string, end: string) => {
    const response = await (await import('./api-client')).apiClient.get('/analytics/production', { params: { start, end } });
    return response.data;
  },
  generateSalesReport: async (start: string, end: string) => {
    const response = await (await import('./api-client')).apiClient.get('/analytics/sales', { params: { start, end } });
    return response.data;
  },
};
