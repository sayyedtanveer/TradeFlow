// Production Dashboard Page.

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  MetricGrid,
  ProductionChart,
  CategoryBreakdownChart,
  KPICard,
} from '../components/Charts';
import { analyticsAPI } from '../../../services/api';

export const ProductionDashboard: React.FC = () => {
  const [dateRange, setDateRange] = useState({
    start: new Date(new Date().getFullYear(), new Date().getMonth(), 1)
      .toISOString()
      .split('T')[0],
    end: new Date().toISOString().split('T')[0],
  });

  // Fetch production report
  const { data: productionReport, isLoading: loadingReport } = useQuery({
    queryKey: ['production-report', dateRange],
    queryFn: () =>
      analyticsAPI.generateProductionReport(dateRange.start, dateRange.end),
  });

  const isLoading = loadingReport;

  if (isLoading) {
    return <div className="p-6">Loading production dashboard...</div>;
  }

  const metrics = [
    {
      title: 'Total Planned',
      value: productionReport?.summary?.total_planned || 0,
      unit: ' units',
      trend: 2,
    },
    {
      title: 'Total Produced',
      value: productionReport?.summary?.total_produced || 0,
      unit: ' units',
      trend: 3,
    },
    {
      title: 'Scrap Quantity',
      value: productionReport?.summary?.total_scrap || 0,
      unit: ' units',
      trend: -5,
    },
    {
      title: 'Efficiency Rate',
      value: `${((productionReport?.summary?.efficiency || 0) * 100).toFixed(1)}`,
      unit: '%',
      trend: 1,
    },
  ];

  const productionData = productionReport?.data?.map((item: any) => ({
    date: item.group,
    planned: item.entries?.[0]?.planned_qty || 0,
    produced: item.entries?.[0]?.produced_qty || 0,
    scrap: item.entries?.[0]?.scrap_qty || 0,
  })) || [];

  const statusData = [
    { name: 'Completed', value: 65 },
    { name: 'In Progress', value: 25 },
    { name: 'Planned', value: 10 },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Production Dashboard</h1>
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

      {/* Production Chart */}
      <ProductionChart data={productionData} title="Production Progress" />

      {/* Status Breakdown */}
      <CategoryBreakdownChart data={statusData} title="Work Order Status" />

      {/* Additional Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KPICard
          title="Completion Rate"
          value={`${((productionReport?.summary?.completion_rate || 0) * 100).toFixed(1)}%`}
          trend={2}
        />
        <KPICard
          title="Scrap Rate"
          value={`${((productionReport?.summary?.scrap_rate || 0) * 100).toFixed(2)}%`}
          trend={-3}
        />
        <KPICard
          title="Active Work Orders"
          value="24"
          trend={1}
        />
      </div>
    </div>
  );
};
