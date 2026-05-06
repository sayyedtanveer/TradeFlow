/**
 * Sales Dashboard Page
 * Overview of sales orders, statistics, and quick actions
 */

import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CardSkeleton } from '@/components/shared/LoadingSkeleton';
import { ordersApi } from '@/services/sales.service';
import { OrderStatistics, SalesOrder, OrderStatus } from '@/types/sales.types';
import { AlertCircle, CheckCircle2, ShoppingCart, Users, FileText } from 'lucide-react';
import { formatCurrency } from '@/utils/currency';
import { REALTIME_EVENT_NAME } from '@/components/notifications/RealtimeNotificationsBridge';

export default function SalesDashboardPage() {
  const navigate = useNavigate();
  const [statistics, setStatistics] = useState<OrderStatistics | null>(null);
  const [recentOrders, setRecentOrders] = useState<SalesOrder[]>([]);
  const [pendingApprovalOrders, setPendingApprovalOrders] = useState<SalesOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(async (silent = false) => {
    try {
      setError(null);
      if (!silent) setLoading(true);
      const today = new Date().toISOString().split('T')[0];
      const ninetyDaysAgo = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      const [stats, pendingOrders, recent] = await Promise.all([
        ordersApi.getStatistics(),
        ordersApi.list(6, 0, undefined, OrderStatus.PENDING_APPROVAL, ninetyDaysAgo, today),
        ordersApi.list(8, 0, undefined, undefined, ninetyDaysAgo, today),
      ]);
      setStatistics(stats);
      setPendingApprovalOrders(pendingOrders.items);
      setRecentOrders(recent.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    const handleRealtime = () => {
      void loadDashboard(true);
    };
    window.addEventListener(REALTIME_EVENT_NAME, handleRealtime);
    return () => window.removeEventListener(REALTIME_EVENT_NAME, handleRealtime);
  }, [loadDashboard]);

  if (loading) {
    return (
      <div className="p-8">
        <CardSkeleton />
      </div>
    );
  }

  const statsCards = [
    {
      title: 'Pending Approval',
      value: statistics?.pending_approval_count || 0,
      icon: AlertCircle,
      color: 'bg-amber-500',
    },
    {
      title: 'Draft Orders',
      value: statistics?.draft_count || 0,
      icon: FileText,
      color: 'bg-slate-500',
    },
    {
      title: 'Ready to Ship',
      value: statistics?.ready_count || 0,
      icon: CheckCircle2,
      color: 'bg-green-500',
    },
    {
      title: 'Shipped',
      value: statistics?.shipped_count || 0,
      icon: Users,
      color: 'bg-purple-500',
    },
  ];

  const getStatusColor = (status: OrderStatus) => {
    const colors: Record<OrderStatus, string> = {
      [OrderStatus.DRAFT]: 'bg-gray-100 text-gray-800',
      [OrderStatus.PENDING_APPROVAL]: 'bg-amber-100 text-amber-800',
      [OrderStatus.APPROVED]: 'bg-indigo-100 text-indigo-800',
      [OrderStatus.REJECTED]: 'bg-red-100 text-red-800',
      [OrderStatus.CONFIRMED]: 'bg-blue-100 text-blue-800',
      [OrderStatus.PROCESSING]: 'bg-sky-100 text-sky-800',
      [OrderStatus.PRODUCTION]: 'bg-yellow-100 text-yellow-800',
      [OrderStatus.READY]: 'bg-purple-100 text-purple-800',
      [OrderStatus.SHIPPED]: 'bg-green-100 text-green-800',
      [OrderStatus.DELIVERED]: 'bg-emerald-100 text-emerald-800',
      [OrderStatus.COMPLETED]: 'bg-teal-100 text-teal-800',
      [OrderStatus.CANCELLED]: 'bg-red-100 text-red-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Sales Dashboard</h1>
          <p className="text-gray-600 mt-2">Monitor your sales orders and client performance</p>
        </div>
        <Button onClick={() => navigate('/sales/orders/new')} size="lg">
          <ShoppingCart className="mr-2 h-4 w-4" />
          New Order
        </Button>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statsCards.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.title}>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-gray-600">{stat.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div className="text-3xl font-bold text-gray-900">{stat.value}</div>
                  <div className={`${stat.color} p-3 rounded-lg`}>
                    <Icon className="h-6 w-6 text-white" />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Approval Queue */}
      <Card className="border-amber-200 bg-amber-50/40">
        <CardHeader className="flex flex-row items-center justify-between gap-4">
          <div>
            <CardTitle>Orders Waiting for Approval</CardTitle>
            <CardDescription>Client portal and admin-submitted orders that need manager review</CardDescription>
          </div>
          <Button variant="outline" onClick={() => navigate('/sales/orders?status=PENDING_APPROVAL')}>
            Open Sales Orders
          </Button>
        </CardHeader>
        <CardContent>
          {pendingApprovalOrders.length === 0 ? (
            <div className="rounded-lg border border-dashed border-amber-200 bg-white p-6 text-center text-sm text-gray-500">
              No orders are waiting for approval right now.
            </div>
          ) : (
            <div className="grid gap-3">
              {pendingApprovalOrders.map((order) => (
                <button
                  key={order.id}
                  onClick={() => navigate(`/sales/orders/${order.id}`)}
                  className="flex flex-col gap-2 rounded-xl border border-amber-200 bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md sm:flex-row sm:items-center sm:justify-between"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-gray-900">{order.order_number}</span>
                      <Badge className={getStatusColor(order.status)}>{order.status}</Badge>
                    </div>
                    <p className="mt-1 text-sm text-gray-500">
                      {order.client_name || order.client_id}
                      {order.client_code ? ` • ${order.client_code}` : ''}
                    </p>
                    <p className="mt-1 text-sm text-gray-700">{order.item_summary || 'No line items'}</p>
                  </div>
                  <div className="text-sm font-semibold text-gray-900">{formatCurrency(order.grand_total || 0)}</div>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent Orders */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Sales Orders</CardTitle>
          <CardDescription>Latest order activity across draft, approval, production, and delivery states</CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}
          {recentOrders.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <p>No recent sales orders found</p>
              <Button
                variant="link"
                onClick={() => navigate('/sales/orders/new')}
                className="mt-2"
              >
                Create First Order
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium text-gray-700">Order #</th>
                    <th className="px-4 py-2 text-left font-medium text-gray-700">Client</th>
                    <th className="px-4 py-2 text-left font-medium text-gray-700">Total</th>
                    <th className="px-4 py-2 text-left font-medium text-gray-700">Status</th>
                    <th className="px-4 py-2 text-right font-medium text-gray-700">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {recentOrders.map((order) => (
                    <tr key={order.id} className="border-b hover:bg-gray-50">
                      <td className="px-4 py-2 font-medium">{order.order_number}</td>
                      <td className="px-4 py-2">
                        <div className="font-medium">{order.client_name || order.client_id}</div>
                        <div className="text-xs text-gray-500">{order.item_summary || 'No line items'}</div>
                      </td>
                      <td className="px-4 py-2">{formatCurrency(order.grand_total)}</td>
                      <td className="px-4 py-2">
                        <Badge className={getStatusColor(order.status)}>{order.status}</Badge>
                      </td>
                      <td className="px-4 py-2 text-right">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => navigate(`/sales/orders/${order.id}`)}
                        >
                          View
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Links */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="cursor-pointer hover:shadow-lg transition-shadow" onClick={() => navigate('/sales/orders')}>
          <CardHeader>
            <CardTitle className="text-lg">All Orders</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600">View and manage all sales orders</p>
          </CardContent>
        </Card>
        <Card className="cursor-pointer hover:shadow-lg transition-shadow" onClick={() => navigate('/sales/clients')}>
          <CardHeader>
            <CardTitle className="text-lg">Clients</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600">Manage client information and credit limits</p>
          </CardContent>
        </Card>
        <Card className="cursor-pointer hover:shadow-lg transition-shadow" onClick={() => navigate('/sales/price-lists')}>
          <CardHeader>
            <CardTitle className="text-lg">Price Lists</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600">Configure pricing and product rates</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
