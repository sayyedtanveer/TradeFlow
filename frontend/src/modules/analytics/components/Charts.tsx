// Chart components for analytics dashboards.

import React from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { formatCurrency } from '@/utils/currency';

interface ChartProps {
  data: any[];
  title?: string;
  height?: number;
}

// Current color palette
const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

export const RevenueChart: React.FC<ChartProps> = ({ data, title = 'Revenue', height = 300 }) => {
  return (
    <div className="w-full bg-white rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip formatter={(value: any) => formatCurrency(value)} />
          <Legend />
          <Line 
            type="monotone" 
            dataKey="revenue" 
            stroke={COLORS[0]} 
            strokeWidth={2}
            dot={{ fill: COLORS[0], r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export const OrdersChart: React.FC<ChartProps> = ({ data, title = 'Orders', height = 300 }) => {
  return (
    <div className="w-full bg-white rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="count" fill={COLORS[1]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export const InventoryChart: React.FC<ChartProps> = ({ data, title = 'Inventory Value', height = 300 }) => {
  return (
    <div className="w-full bg-white rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip formatter={(value: any) => formatCurrency(value)} />
          <Legend />
          <Line 
            type="monotone" 
            dataKey="value" 
            stroke={COLORS[4]} 
            strokeWidth={2}
            dot={{ fill: COLORS[4], r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export const CategoryBreakdownChart: React.FC<{ data: any[]; title?: string }> = ({ 
  data, 
  title = 'Category Breakdown' 
}) => {
  return (
    <div className="w-full bg-white rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }: any) => `${name} ${(percent * 100).toFixed(0)}%`}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((_entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(value: any) => value.toLocaleString()} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

export const KPICard: React.FC<{
  title: string;
  value: string | number;
  unit?: string;
  trend?: number;
  icon?: React.ReactNode;
}> = ({ title, value, unit = '', trend, icon }) => {
  const trendColor = trend && trend > 0 ? 'text-green-600' : 'text-red-600';
  const trendText = trend && trend !== 0 ? `${trend > 0 ? '+' : ''}${trend}%` : '';

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-2">
            {value}{unit}
          </p>
          {trendText && (
            <p className={`text-sm mt-2 ${trendColor}`}>
              {trendText}
            </p>
          )}
        </div>
        {icon && <div className="text-3xl text-gray-300">{icon}</div>}
      </div>
    </div>
  );
};

export const MetricGrid: React.FC<{
  metrics: Array<{ 
    title: string; 
    value: number | string; 
    unit?: string; 
    trend?: number;
  }>;
}> = ({ metrics }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {metrics.map((metric, idx) => (
        <KPICard 
          key={idx}
          title={metric.title}
          value={metric.value}
          unit={metric.unit}
          trend={metric.trend}
        />
      ))}
    </div>
  );
};
