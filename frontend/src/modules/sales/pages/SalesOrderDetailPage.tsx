/**
 * Sales Order Detail Page
 * View complete order details, line items, and perform status transitions
 */

import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CardSkeleton } from '@/components/shared/LoadingSkeleton';
import { ordersApi } from '@/services/sales.service';
import { SalesOrder, OrderStatus } from '@/types/sales.types';
import { ArrowLeft, Edit2, CheckCircle, Truck, Package, Trash2, Plus } from 'lucide-react';
import { Input } from '@/components/ui/input';

export default function SalesOrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [order, setOrder] = useState<SalesOrder | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  
  // New Line Item State
  const [newLine, setNewLine] = useState({
    product_id: '',
    product_type: 'variant',
    uom_id: '',
    quantity: 1,
    tax_rate: 0
  });

  useEffect(() => {
    const loadOrder = async () => {
      if (!id) return;
      try {
        setError(null);
        const data = await ordersApi.get(id);
        setOrder(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load order');
      } finally {
        setLoading(false);
      }
    };

    loadOrder();
  }, [id]);

  const handleStatusChange = async (action: 'confirm' | 'ship' | 'deliver' | 'cancel') => {
    if (!order) return;

    setActionLoading(true);
    try {
      let updated: SalesOrder;
      switch (action) {
        case 'confirm':
          updated = await ordersApi.confirm(order.id);
          break;
        case 'ship':
          updated = await ordersApi.ship(order.id);
          break;
        case 'deliver':
          updated = await ordersApi.deliver(order.id);
          break;
        case 'cancel':
          updated = await ordersApi.cancel(order.id);
          break;
      }
      setOrder(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddLine = async () => {
    if (!order || !newLine.product_id || !newLine.uom_id || newLine.quantity <= 0) {
      setError('Please provide product ID, UOM ID, and a valid quantity');
      return;
    }
    setActionLoading(true);
    try {
      const updated = await ordersApi.addLine(order.id, {
        product_id: newLine.product_id,
        product_type: newLine.product_type as 'variant' | 'finished_product',
        uom_id: newLine.uom_id,
        quantity: newLine.quantity,
        tax_rate: newLine.tax_rate,
      });
      setOrder(updated);
      setNewLine({ ...newLine, product_id: '', quantity: 1 });
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add line item');
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusColor = (status: OrderStatus) => {
    const colors: Record<OrderStatus, string> = {
      [OrderStatus.DRAFT]: 'bg-gray-100 text-gray-800',
      [OrderStatus.CONFIRMED]: 'bg-blue-100 text-blue-800',
      [OrderStatus.PRODUCTION]: 'bg-yellow-100 text-yellow-800',
      [OrderStatus.READY]: 'bg-purple-100 text-purple-800',
      [OrderStatus.SHIPPED]: 'bg-green-100 text-green-800',
      [OrderStatus.DELIVERED]: 'bg-emerald-100 text-emerald-800',
      [OrderStatus.CANCELLED]: 'bg-red-100 text-red-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <div className="p-8">
        <CardSkeleton />
      </div>
    );
  }

  if (!order) {
    return (
      <div className="p-8">
        <div className="text-center">
          <p className="text-red-600 mb-4">Order not found</p>
          <Button onClick={() => navigate('/sales/orders')}>Back to Orders</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate('/sales/orders')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Order {order.order_number}</h1>
            <p className="text-gray-600">View and manage order details</p>
          </div>
        </div>
        <div className="flex gap-2">
          {order.status === OrderStatus.DRAFT && (
            <Button variant="outline" onClick={() => navigate(`/sales/orders/${order.id}/edit`)}>
              <Edit2 className="mr-2 h-4 w-4" />
              Edit
            </Button>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Order Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Status</CardTitle>
          </CardHeader>
          <CardContent>
            <Badge className={getStatusColor(order.status)}>{order.status}</Badge>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Order Date</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">{new Date(order.order_date).toLocaleDateString()}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Delivery Date</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">
              {new Date(order.delivery_date).toLocaleDateString()}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Grand Total</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold text-green-600">${order.grand_total.toFixed(2)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Order Details */}
      <Card>
        <CardHeader>
          <CardTitle>Order Information</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">Client ID</label>
            <p className="text-gray-900">{order.client_id}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">Payment Status</label>
            <p className="text-gray-900">{order.payment_status}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">Created By</label>
            <p className="text-gray-900">{order.created_by || 'System'}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">Created At</label>
            <p className="text-gray-900">{new Date(order.created_at).toLocaleString()}</p>
          </div>
          {order.notes && (
            <div className="col-span-full">
              <label className="text-sm font-medium text-gray-700 block mb-1">Notes</label>
              <p className="text-gray-900 bg-gray-50 p-3 rounded">{order.notes}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Line Items */}
      <Card>
        <CardHeader>
          <CardTitle>Order Line Items</CardTitle>
          <CardDescription>Products included in this order</CardDescription>
        </CardHeader>
        <CardContent>
          {order.lines.length === 0 ? (
            <p className="text-gray-500 text-center py-4">No line items</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium text-gray-700">Product</th>
                    <th className="px-4 py-2 text-left font-medium text-gray-700">Quantity</th>
                    <th className="px-4 py-2 text-left font-medium text-gray-700">Unit Price</th>
                    <th className="px-4 py-2 text-left font-medium text-gray-700">Allocated</th>
                    <th className="px-4 py-2 text-left font-medium text-gray-700">Shipped</th>
                    <th className="px-4 py-2 text-right font-medium text-gray-700">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {order.lines.map((line) => (
                    <tr key={line.id} className="border-b hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="font-medium">{line.product_id}</div>
                        <div className="text-xs text-gray-500">{line.product_type}</div>
                      </td>
                      <td className="px-4 py-3">{line.quantity}</td>
                      <td className="px-4 py-3">${line.unit_price.toFixed(2)}</td>
                      <td className="px-4 py-3">
                        <Badge variant="outline">{line.allocated_qty}</Badge>
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant="outline">{line.shipped_qty}</Badge>
                      </td>
                      <td className="px-4 py-3 text-right font-semibold">${line.total.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          
          {order.status === OrderStatus.DRAFT && (
            <div className="mt-6 border-t pt-6">
              <h4 className="font-semibold mb-4 text-gray-800">Add Line Item</h4>
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-end">
                <div className="col-span-2">
                  <label className="text-sm font-medium text-gray-700 block mb-1">Product Variant ID *</label>
                  <Input 
                    placeholder="UUID of Variant"
                    value={newLine.product_id}
                    onChange={(e) => setNewLine({ ...newLine, product_id: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700 block mb-1">UOM ID *</label>
                  <Input 
                    placeholder="UUID of UOM"
                    value={newLine.uom_id}
                    onChange={(e) => setNewLine({ ...newLine, uom_id: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700 block mb-1">Quantity *</label>
                  <Input 
                    type="number"
                    min="1"
                    value={newLine.quantity}
                    onChange={(e) => setNewLine({ ...newLine, quantity: parseFloat(e.target.value) || 0 })}
                  />
                </div>
                <div>
                  <Button 
                    className="w-full bg-slate-800 hover:bg-slate-700" 
                    onClick={handleAddLine}
                    disabled={actionLoading}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add
                  </Button>
                </div>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                * Note: Pricing is automatically resolved from the Client's assigned Price List or the Default Price List. 
                Auto-Work Order generation occurs on confirm if no physical stock is available.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Totals */}
      <Card>
        <CardHeader>
          <CardTitle>Order Totals</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex justify-between text-gray-600">
              <span>Subtotal:</span>
              <span>${order.subtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-gray-600">
              <span>Discount:</span>
              <span className="text-red-600">-${order.discount_amount.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-gray-600">
              <span>Tax:</span>
              <span>${order.tax_amount.toFixed(2)}</span>
            </div>
            <div className="border-t pt-3 flex justify-between text-lg font-bold">
              <span>Grand Total:</span>
              <span className="text-green-600">${order.grand_total.toFixed(2)}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <Card>
        <CardHeader>
          <CardTitle>Order Actions</CardTitle>
        </CardHeader>
        <CardContent className="flex gap-3 flex-wrap">
          {order.status === OrderStatus.DRAFT && (
            <>
              <Button
                onClick={() => handleStatusChange('confirm')}
                disabled={actionLoading}
                className="bg-blue-600 hover:bg-blue-700"
              >
                <CheckCircle className="mr-2 h-4 w-4" />
                Confirm Order
              </Button>
              <Button
                variant="destructive"
                onClick={() => handleStatusChange('cancel')}
                disabled={actionLoading}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Cancel
              </Button>
            </>
          )}
          {order.status === OrderStatus.CONFIRMED && (
            <Button
              onClick={() => handleStatusChange('ship')}
              disabled={actionLoading}
              className="bg-green-600 hover:bg-green-700"
            >
              <Truck className="mr-2 h-4 w-4" />
              Mark As Shipped
            </Button>
          )}
          {order.status === OrderStatus.SHIPPED && (
            <Button
              onClick={() => handleStatusChange('deliver')}
              disabled={actionLoading}
              className="bg-emerald-600 hover:bg-emerald-700"
            >
              <Package className="mr-2 h-4 w-4" />
              Mark As Delivered
            </Button>
          )}
          {order.status !== OrderStatus.DELIVERED && order.status !== OrderStatus.CANCELLED && (
            <Button
              variant="outline"
              onClick={() => handleStatusChange('cancel')}
              disabled={actionLoading}
            >
              Cancel Order
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
