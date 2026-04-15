// Finance Dashboard Page.

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  MetricGrid,
  InventoryChart,
  CategoryBreakdownChart,
  KPICard,
} from '../components/Charts';
import { analyticsAPI } from '../../../services/api';

export const FinanceDashboard: React.FC = () => {
  const [dateRange, setDateRange] = useState({
    start: new Date(new Date().getFullYear(), new Date().getMonth(), 1)
      .toISOString()
      .split('T')[0],
    end: new Date().toISOString().split('T')[0],
  });

  // Fetch finance report
  const { data: financeReport, isLoading: loadingReport } = useQuery({
    queryKey: ['finance-report', dateRange],
    queryFn: () =>
      analyticsAPI.generateFinanceReport(dateRange.start, dateRange.end),
  });

  // Fetch dashboard summary
  const { data: _dashboard } = useQuery({
    queryKey: ['dashboard-summary', dateRange],
    queryFn: () =>
      analyticsAPI.getDashboardSummary(dateRange.start, dateRange.end),
  });

  const isLoading = loadingReport;

  if (isLoading) {
    return <div className="p-6">Loading finance dashboard...</div>;
  }

  const metrics = [
    {
      title: 'Total AR',
      value: `$${(financeReport?.summary?.ar_total || 0).toLocaleString()}`,
    },
    {
      title: 'Total AP',
      value: `$${(financeReport?.summary?.ap_total || 0).toLocaleString()}`,
    },
    {
      title: 'AR Outstanding',
      value: `$${(financeReport?.summary?.ar_outstanding || 0).toLocaleString()}`,
      trend: -2,
    },
    {
      title: 'AP Outstanding',
      value: `$${(financeReport?.summary?.ap_outstanding || 0).toLocaleString()}`,
      trend: 1,
    },
  ];

  const cashFlowData = financeReport?.data?.map((item: any) => ({
    date: item.group,
    ar: item.entries?.[0]?.ar_amount || 0,
    ap: item.entries?.[0]?.ap_amount || 0,
  })) || [];

  const arApData = [
    { name: 'AR Collected', value: financeReport?.summary?.ar_collected || 0 },
    { name: 'AR Outstanding', value: financeReport?.summary?.ar_outstanding || 0 },
    { name: 'AP Paid', value: financeReport?.summary?.ap_paid || 0 },
    { name: 'AP Outstanding', value: financeReport?.summary?.ap_outstanding || 0 },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Finance Dashboard</h1>
        <div className="flex gap-2">
          <input
            type="date"
            value={dateRange.start}
            onChange={(e) =>
              setDateRange({ ...dateRange, start: e.target.value })
            }
            className="px-3 py-2 border border-gray-300 rounded-md"
          />
          <input
            type="date"
            value={dateRange.end}
            onChange={(e) =>
              setDateRange({ ...dateRange, end: e.target.value })
            }
            className="px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>
      </div>

      {/* KPI Metrics */}
      <MetricGrid metrics={metrics} />

      {/* Cash Flow Chart */}
      <InventoryChart data={cashFlowData} title="AR/AP Trend" />

      {/* Cash Position Breakdown */}
      <CategoryBreakdownChart data={arApData} title="Cash Position Breakdown" />

      {/* Financial Health Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KPICard
          title="DSO (Days)"
          value={financeReport?.summary?.dso?.toFixed(1) || '0'}
          unit=" days"
        />
        <KPICard
          title="DPO (Days)"
          value={financeReport?.summary?.dpo?.toFixed(1) || '0'}
          unit=" days"
        />
        <KPICard
          title="Cash Conversion Cycle"
          value={financeReport?.summary?.cash_conversion_cycle?.toFixed(1) || '0'}
          unit=" days"
        />
      </div>

      {/* Cash Position */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Cash Position Summary</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="text-center">
            <p className="text-gray-600 text-sm mb-2">Receivables</p>
            <p className="text-3xl font-bold text-green-600">
              ${(financeReport?.summary?.ar_total || 0).toLocaleString()}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              {financeReport?.summary?.ar_collected || 0} collected
            </p>
          </div>
          <div className="text-center">
            <p className="text-gray-600 text-sm mb-2">Payables</p>
            <p className="text-3xl font-bold text-red-600">
              ${(financeReport?.summary?.ap_total || 0).toLocaleString()}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              {financeReport?.summary?.ap_paid || 0} paid
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
