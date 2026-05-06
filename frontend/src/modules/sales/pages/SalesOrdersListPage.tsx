/**
 * Sales Orders List Page
 * Display all sales orders with filtering, search, and bulk actions
 */

import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TableSkeleton } from '@/components/shared/LoadingSkeleton';
import { ordersApi } from '@/services/sales.service';
import { SalesOrder, OrderStatus } from '@/types/sales.types';
import { Plus, Filter, Eye, ShoppingCart } from 'lucide-react';
import { formatCurrency } from '@/utils/currency';
import { REALTIME_EVENT_NAME } from '@/components/notifications/RealtimeNotificationsBridge';

export default function SalesOrdersListPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<string>(searchParams.get('status') || 'all');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(10);

  const handleStatusChange = (nextStatus: string) => {
    setStatus(nextStatus);
    setCurrentPage(1);
    const next = new URLSearchParams(searchParams);
    if (nextStatus === 'all') {
      next.delete('status');
    } else {
      next.set('status', nextStatus);
    }
    setSearchParams(next, { replace: true });
  };

  const loadOrders = useCallback(async (silent = false) => {
    try {
      setError(null);
      if (!silent) setLoading(true);
      const offset = (currentPage - 1) * pageSize;

      // Get today's date for default date range
      const today = new Date().toISOString().split('T')[0];
      const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      const selectedStatus = status === 'all' ? undefined : (status as OrderStatus);

      const response = await ordersApi.list(
        pageSize,
        offset,
        undefined,
        selectedStatus,
        thirtyDaysAgo, // Default to last 30 days
        today
      );
      const searchTerm = search.trim().toLowerCase();
      const visibleOrders = searchTerm
        ? response.items.filter((order) => order.order_number.toLowerCase().includes(searchTerm))
        : response.items;

      setOrders(visibleOrders);
      setTotal(searchTerm ? visibleOrders.length : response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load orders');
    } finally {
      if (!silent) setLoading(false);
    }
  }, [currentPage, pageSize, search, status]);

  useEffect(() => {
    void loadOrders();
  }, [loadOrders]);

  useEffect(() => {
    const handleRealtime = () => {
      void loadOrders(true);
    };
    window.addEventListener(REALTIME_EVENT_NAME, handleRealtime);
    return () => window.removeEventListener(REALTIME_EVENT_NAME, handleRealtime);
  }, [loadOrders]);

  const getStatusColor = (orderStatus: OrderStatus) => {
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
    return colors[orderStatus] || 'bg-gray-100 text-gray-800';
  };

  if (loading && orders.length === 0) {
    return (
      <div className="p-8">
        <TableSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Sales Orders</h1>
          <p className="text-gray-600 mt-1">Manage and track all sales orders</p>
        </div>
        <Button onClick={() => navigate('/sales/orders/new')} size="lg">
          <Plus className="mr-2 h-4 w-4" />
          New Order
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Filters</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-2">Search</label>
              <Input
                placeholder="Search by order number..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-2">Status</label>
              <Select value={status} onValueChange={handleStatusChange}>
                <SelectTrigger>
                  <SelectValue placeholder="All Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  {Object.values(OrderStatus).map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end">
              <Button variant="outline" className="w-full">
                <Filter className="mr-2 h-4 w-4" />
                Apply
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Orders Table */}
      <Card>
        <CardHeader>
          <CardTitle>Orders</CardTitle>
          <CardDescription>Showing {orders.length} of {total} orders</CardDescription>
        </CardHeader>
        <CardContent>
          {orders.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <ShoppingCart className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p>No orders found</p>
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
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Order Number</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Client</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Requested Items</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Order Date</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Delivery Date</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Total</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Status</th>
                    <th className="px-4 py-3 text-right font-semibold text-gray-700">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((order) => (
                    <tr key={order.id} className="border-b hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium">{order.order_number}</td>
                      <td className="px-4 py-3">
                        <div className="font-medium">{order.client_name || order.client_id}</div>
                        {order.client_code && (
                          <div className="text-xs text-gray-500">{order.client_code}</div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="max-w-xs text-sm text-gray-900">{order.item_summary || 'No line items'}</div>
                        <div className="text-xs text-gray-500">{order.item_count || 0} item(s)</div>
                      </td>
                      <td className="px-4 py-3">{new Date(order.order_date).toLocaleDateString()}</td>
                      <td className="px-4 py-3">{new Date(order.delivery_date).toLocaleDateString()}</td>
                      <td className="px-4 py-3 font-semibold">{formatCurrency(order.grand_total || 0)}</td>
                      <td className="px-4 py-3">
                        <Badge className={getStatusColor(order.status)}>{order.status}</Badge>
                      </td>
                      <td className="px-4 py-3 text-right space-x-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/sales/orders/${order.id}`)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {total > pageSize && (
            <div className="flex justify-between items-center mt-4 pt-4 border-t">
              <span className="text-sm text-gray-600">
                Page {currentPage} of {Math.ceil(total / pageSize)}
              </span>
              <div className="space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={currentPage >= Math.ceil(total / pageSize)}
                  onClick={() => setCurrentPage(currentPage + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
