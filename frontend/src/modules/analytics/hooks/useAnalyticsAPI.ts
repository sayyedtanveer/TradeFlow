// Analytics API service.

import { API_BASE_URL } from '../../../config/constants';

interface ReportConfig {
  name: string;
  description?: string;
  type: string;
  query_config: {
    metrics: string[];
    filters: Record<string, any>;
    grouping?: string;
    sort_by?: string;
    sort_direction?: string;
    limit?: number;
  };
  is_public: boolean;
}

class AnalyticsService {
  private baseUrl = `${API_BASE_URL}/analytics`;

  // Reports Management
  async createSavedReport(config: ReportConfig): Promise<any> {
    const response = await fetch(`${this.baseUrl}/reports`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify({
        name: config.name,
        description: config.description,
        report_type: config.type,
        query_config: config.query_config,
        is_public: config.is_public,
      }),
    });
    return response.json();
  }

  async listSavedReports(isPublic?: boolean): Promise<any[]> {
    const params = new URLSearchParams();
    if (isPublic !== undefined) params.append('is_public', String(isPublic));

    const response = await fetch(`${this.baseUrl}/reports?${params}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
    });
    return response.json();
  }

  async getSavedReport(reportId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/reports/${reportId}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
    });
    return response.json();
  }

  async deleteSavedReport(reportId: string): Promise<void> {
    await fetch(`${this.baseUrl}/reports/${reportId}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
    });
  }

  // Report Generation
  async generateSalesReport(
    startDate: string,
    endDate: string,
    grouping?: string
  ): Promise<any> {
    const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
    if (grouping) params.append('grouping', grouping);

    const response = await fetch(`${this.baseUrl}/sales-report?${params}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
    });
    return response.json();
  }

  async generateProductionReport(
    startDate: string,
    endDate: string,
    grouping?: string
  ): Promise<any> {
    const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
    if (grouping) params.append('grouping', grouping);

    const response = await fetch(`${this.baseUrl}/production-report?${params}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
    });
    return response.json();
  }

  async generateInventoryReport(
    startDate: string,
    endDate: string,
    grouping?: string
  ): Promise<any> {
    const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
    if (grouping) params.append('grouping', grouping);

    const response = await fetch(`${this.baseUrl}/inventory-report?${params}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
    });
    return response.json();
  }

  async generateFinanceReport(
    startDate: string,
    endDate: string,
    grouping?: string
  ): Promise<any> {
    const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
    if (grouping) params.append('grouping', grouping);

    const response = await fetch(`${this.baseUrl}/finance-report?${params}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
    });
    return response.json();
  }

  async getDashboardSummary(periodStart: string, periodEnd: string): Promise<any> {
    const params = new URLSearchParams({ period_start: periodStart, period_end: periodEnd });

    const response = await fetch(`${this.baseUrl}/dashboard-summary?${params}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
    });
    return response.json();
  }

  async executeReport(reportId: string, exportFormat: string = 'none'): Promise<any> {
    const params = new URLSearchParams({ export_format: exportFormat });

    const response = await fetch(`${this.baseUrl}/reports/${reportId}/execute?${params}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
    });
    return response.json();
  }

  async getExecutionHistory(reportId?: string, limit: number = 100): Promise<any[]> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (reportId) params.append('report_id', reportId);

    const response = await fetch(`${this.baseUrl}/execution-history?${params}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
    });
    return response.json();
  }
}

export const analyticsAPI = new AnalyticsService();
