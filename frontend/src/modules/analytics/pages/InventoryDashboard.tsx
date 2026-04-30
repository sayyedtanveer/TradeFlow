// Inventory Dashboard Page.

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  MetricGrid,
  InventoryChart,
  CategoryBreakdownChart,
  KPICard,
} from '../components/Charts';
import { analyticsAPI } from '../../../services/api';
import { formatCurrency } from '@/utils/currency';

export const InventoryDashboard: React.FC = () => {
  const [dateRange, setDateRange] = useState({
    start: new Date(new Date().getFullYear(), new Date().getMonth(), 1)
      .toISOString()
      .split('T')[0],
    end: new Date().toISOString().split('T')[0],
  });

  // Fetch inventory report
  const { data: inventoryReport, isLoading: loadingReport } = useQuery({
    queryKey: ['inventory-report', dateRange],
    queryFn: () =>
      analyticsAPI.generateInventoryReport(dateRange.start, dateRange.end),
  });

  const isLoading = loadingReport;

  if (isLoading) {
    return <div className="p-6">Loading inventory dashboard...</div>;
  }

  const metrics = [
    {
      title: 'Total Inventory Value',
      value: formatCurrency(inventoryReport?.summary?.total_value || 0),
      trend: 2,
    },
    {
      title: 'Total Items',
      value: inventoryReport?.summary?.total_items || 0,
      trend: 1,
    },
    {
      title: 'Fast-Moving Items',
      value: inventoryReport?.summary?.fast_moving || 0,
    },
    {
      title: 'Stockouts',
      value: inventoryReport?.summary?.stockouts || 0,
      trend: -3,
    },
  ];

  const inventoryData = inventoryReport?.data?.map((item: any) => ({
    date: item.group,
    value: item.entries?.[0]?.value || 0,
  })) || [];

  const categoryData = [
    { name: 'Raw Materials', value: 4500 },
    { name: 'Semi-Finished', value: 3200 },
    { name: 'Finished Goods', value: 5800 },
    { name: 'Packaging', value: 1200 },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Inventory Dashboard</h1>
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

      {/* Inventory Value Chart */}
      <InventoryChart data={inventoryData} title="Inventory Value Trend" />

      {/* Inventory by Category */}
      <CategoryBreakdownChart data={categoryData} title="Inventory by Category" />

      {/* Inventory Health */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KPICard
          title="Average Stock Level"
          value={`${(inventoryReport?.summary?.average_stock_level || 0).toFixed(0)}`}
          unit=" units"
        />
        <KPICard
          title="Slow-Moving Items"
          value={inventoryReport?.summary?.slow_moving || 0}
          trend={-1}
        />
        <KPICard
          title="Turnover Rate"
          value="2.5x"
          trend={5}
        />
      </div>
    </div>
  );
};
