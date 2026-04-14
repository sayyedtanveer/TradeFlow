"""Main Analytics Index Page."""

import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { ReportBuilder } from '../components/ReportBuilder';
import { SalesDashboard } from './SalesDashboard';
import { ProductionDashboard } from './ProductionDashboard';
import { InventoryDashboard } from './InventoryDashboard';
import { FinanceDashboard } from './FinanceDashboard';

export const AnalyticsPage: React.FC = () => {
  const [activeView, setActiveView] = useState<
    'sales' | 'production' | 'inventory' | 'finance' | 'builder'
  >('sales');

  const dashboards = [
    { id: 'sales', label: 'Sales', icon: '📊' },
    { id: 'production', label: 'Production', icon: '🏭' },
    { id: 'inventory', label: 'Inventory', icon: '📦' },
    { id: 'finance', label: 'Finance', icon: '💰' },
    { id: 'builder', label: 'Report Builder', icon: '🔨' },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <h1 className="text-2xl font-bold text-gray-900">Analytics & Reporting</h1>
          </div>

          {/* Dashboard Tabs */}
          <div className="flex border-b border-gray-200 overflow-x-auto">
            {dashboards.map((dash) => (
              <button
                key={dash.id}
                onClick={() => setActiveView(dash.id as any)}
                className={`flex items-center gap-2 px-6 py-4 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                  activeView === dash.id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                <span>{dash.icon}</span>
                {dash.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeView === 'sales' && <SalesDashboard />}
        {activeView === 'production' && <ProductionDashboard />}
        {activeView === 'inventory' && <InventoryDashboard />}
        {activeView === 'finance' && <FinanceDashboard />}
        {activeView === 'builder' && <ReportBuilder />}
      </div>
    </div>
  );
};
