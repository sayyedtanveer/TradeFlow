// Sales Dashboard Page.

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  MetricGrid,
  RevenueChart,
  OrdersChart,
  CategoryBreakdownChart,
} from '../components/Charts';
import { analyticsAPI } from '../../../services/api';

export const SalesDashboard: React.FC = () => {
  const [dateRange, setDateRange] = useState({
    start: new Date(new Date().getFullYear(), new Date().getMonth(), 1)
      .toISOString()
      .split('T')[0],
    end: new Date().toISOString().split('T')[0],
  });

  // Fetch sales report data
  const { data: salesReport, isLoading: loadingSalesReport } = useQuery({
    queryKey: ['sales-report', dateRange],
    queryFn: () =>
      analyticsAPI.generateSalesReport(dateRange.start, dateRange.end),
  });

  // Fetch dashboard summary
  const { data: dashboard, isLoading: loadingDashboard } = useQuery({
    queryKey: ['dashboard-summary', dateRange],
    queryFn: () =>
      analyticsAPI.getDashboardSummary(dateRange.start, dateRange.end),
  });

  const isLoading = loadingSalesReport || loadingDashboard;

  if (isLoading) {
    return <div className="p-6">Loading sales dashboard...</div>;
  }

  const metrics = [
    {
      title: 'Total Revenue',
      value: `$${(salesReport?.summary?.total_revenue || 0).toLocaleString()}`,
      trend: 5,
    },
    {
      title: 'Total Orders',
      value: salesReport?.summary?.total_orders || 0,
      trend: 3,
    },
    {
      title: 'Avg Order Value',
      value: `$${(salesReport?.summary?.average_order_value || 0).toFixed(2)}`,
      trend: -2,
    },
    {
      title: 'Pending Orders',
      value: dashboard?.summary?.sales?.orders || 0,
      trend: 1,
    },
  ];

  // Transform data for charts
  const revenueData = salesReport?.data?.map((item: any) => ({
    date: item.group,
    revenue: item.entries?.[0]?.revenue || 0,
  })) || [];

  const ordersData = salesReport?.data?.map((item: any) => ({
    date: item.group,
    count: item.count,
  })) || [];

  const categoryData = [
    { name: 'Electronics', value: 4000 },
    { name: 'Clothing', value: 3000 },
    { name: 'Food', value: 2000 },
    { name: 'Other', value: 1500 },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Sales Dashboard</h1>
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

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RevenueChart data={revenueData} title="Revenue Trend" />
        <OrdersChart data={ordersData} title="Orders by Period" />
      </div>

      <CategoryBreakdownChart data={categoryData} title="Sales by Category" />

      {/* Detailed Table */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <h2 className="text-xl font-bold mb-4">Sales Details</h2>
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Period
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Revenue
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Orders
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {salesReport?.data?.map((item: any, idx: number) => (
                <tr key={idx}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    {item.group}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    ${item.entries?.[0]?.revenue?.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{item.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
