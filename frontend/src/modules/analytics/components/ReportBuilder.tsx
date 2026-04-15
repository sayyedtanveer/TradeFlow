// Report Builder and Scheduler Component.

import React, { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { analyticsAPI } from '../../../services/api';

interface ReportConfig {
  name: string;
  description: string;
  type: 'sales' | 'production' | 'inventory' | 'finance';
  metrics: string[];
  filters: Record<string, any>;
  grouping: string;
  isPublic: boolean;
}

interface ScheduleConfig {
  schedule_type: 'daily' | 'weekly' | 'monthly';
  schedule_time: string;
  day_of_week?: string;
  day_of_month?: number;
  recipients: string[];
}

export const ReportBuilder: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'builder' | 'scheduler' | 'history'>('builder');
  const [reportConfig, setReportConfig] = useState<ReportConfig>({
    name: '',
    description: '',
    type: 'sales',
    metrics: [],
    filters: {},
    grouping: 'date',
    isPublic: false,
  });
  const [scheduleConfig, setScheduleConfig] = useState<ScheduleConfig>({
    schedule_type: 'daily',
    schedule_time: '08:00',
    recipients: [],
  });

  // Fetch saved reports
  const { data: savedReports } = useQuery({
    queryKey: ['saved-reports'],
    queryFn: () => analyticsAPI.listSavedReports(),
  });

  // Create report mutation
  const createReportMutation = useMutation({
    mutationFn: (config: ReportConfig) => analyticsAPI.createSavedReport(config),
    onSuccess: () => {
      alert('Report saved successfully!');
      setReportConfig({
        name: '',
        description: '',
        type: 'sales',
        metrics: [],
        filters: {},
        grouping: 'date',
        isPublic: false,
      });
    },
  });

  const handleSaveReport = () => {
    if (!reportConfig.name.trim()) {
      alert('Please enter a report name');
      return;
    }
    createReportMutation.mutate(reportConfig);
  };

  const metricOptions = {
    sales: ['revenue', 'order_count', 'average_order_value'],
    production: ['planned_qty', 'produced_qty', 'scrap_rate', 'efficiency'],
    inventory: ['stock_level', 'inventory_value', 'turnover_rate', 'stockouts'],
    finance: ['ar_total', 'ap_total', 'cash_position', 'dso'],
  };

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        {(['builder', 'scheduler', 'history'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-4 px-6 text-center font-medium capitalize ${
              activeTab === tab
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="p-6">
        {activeTab === 'builder' && (
          <div className="space-y-6">
            <h2 className="text-xl font-bold">Report Builder</h2>

            {/* Report Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Report Name
              </label>
              <input
                type="text"
                value={reportConfig.name}
                onChange={(e) =>
                  setReportConfig({ ...reportConfig, name: e.target.value })
                }
                placeholder="e.g., Monthly Sales Analysis"
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <textarea
                value={reportConfig.description}
                onChange={(e) =>
                  setReportConfig({ ...reportConfig, description: e.target.value })
                }
                placeholder="Optional description..."
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                rows={3}
              />
            </div>

            {/* Report Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Report Type
              </label>
              <select
                value={reportConfig.type}
                onChange={(e) =>
                  setReportConfig({
                    ...reportConfig,
                    type: e.target.value as any,
                    metrics: [],
                  })
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="sales">Sales</option>
                <option value="production">Production</option>
                <option value="inventory">Inventory</option>
                <option value="finance">Finance</option>
              </select>
            </div>

            {/* Metrics */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Metrics to Include
              </label>
              <div className="space-y-2">
                {metricOptions[reportConfig.type].map((metric) => (
                  <label key={metric} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={reportConfig.metrics.includes(metric)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setReportConfig({
                            ...reportConfig,
                            metrics: [...reportConfig.metrics, metric],
                          });
                        } else {
                          setReportConfig({
                            ...reportConfig,
                            metrics: reportConfig.metrics.filter(
                              (m) => m !== metric
                            ),
                          });
                        }
                      }}
                      className="mr-2 rounded"
                    />
                    <span className="text-sm text-gray-700 capitalize">
                      {metric.replace('_', ' ')}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            {/* Grouping */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Group By
              </label>
              <select
                value={reportConfig.grouping}
                onChange={(e) =>
                  setReportConfig({ ...reportConfig, grouping: e.target.value })
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="date">Date</option>
                <option value="category">Category</option>
                <option value="client">Client</option>
                <option value="product">Product</option>
              </select>
            </div>

            {/* Public */}
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={reportConfig.isPublic}
                onChange={(e) =>
                  setReportConfig({ ...reportConfig, isPublic: e.target.checked })
                }
                className="mr-2 rounded"
              />
              <span className="text-sm text-gray-700">Make this report public</span>
            </label>

            {/* Save Button */}
            <button
              onClick={handleSaveReport}
              disabled={createReportMutation.isPending}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400"
            >
              {createReportMutation.isPending ? 'Saving...' : 'Save Report'}
            </button>
          </div>
        )}

        {activeTab === 'scheduler' && (
          <div className="space-y-6">
            <h2 className="text-xl font-bold">Schedule Report</h2>

            {/* Select Report */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Report
              </label>
              <select className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                <option value="">Choose a report...</option>
                {savedReports?.map((report: any) => (
                  <option key={report.id} value={report.id}>
                    {report.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Schedule Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Frequency
              </label>
              <select
                value={scheduleConfig.schedule_type}
                onChange={(e) =>
                  setScheduleConfig({
                    ...scheduleConfig,
                    schedule_type: e.target.value as any,
                  })
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>

            {/* Time */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Time
              </label>
              <input
                type="time"
                value={scheduleConfig.schedule_time}
                onChange={(e) =>
                  setScheduleConfig({
                    ...scheduleConfig,
                    schedule_time: e.target.value,
                  })
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Recipients */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Recipients (Email)
              </label>
              <input
                type="text"
                placeholder="email1@example.com, email2@example.com"
                value={scheduleConfig.recipients.join(', ')}
                onChange={(e) =>
                  setScheduleConfig({
                    ...scheduleConfig,
                    recipients: e.target.value
                      .split(',')
                      .map((e) => e.trim())
                      .filter((e) => e),
                  })
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Create Schedule Button */}
            <button className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700">
              Create Schedule
            </button>
          </div>
        )}

        {activeTab === 'history' && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold mb-4">Execution History</h2>
            <div className="bg-gray-50 p-4 rounded-md">
              <p className="text-gray-600">No executions yet</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
