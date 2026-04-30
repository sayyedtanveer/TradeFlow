/**
 * Clients List Page
 * Display all sales clients with management options
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TableSkeleton } from '@/components/shared/LoadingSkeleton';
import { clientsApi } from '@/services/sales.service';
import { SalesClient } from '@/types/sales.types';
import { Plus, Edit2, IndianRupee } from 'lucide-react';
import { formatCurrency } from '@/utils/currency';

export default function ClientsListPage() {
  const navigate = useNavigate();
  const [clients, setClients] = useState<SalesClient[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(10);

  useEffect(() => {
    const loadClients = async () => {
      try {
        setError(null);
        setLoading(true);
        const offset = (currentPage - 1) * pageSize;
        const response = await clientsApi.list(pageSize, offset, search);
        setClients(response.items);
        setTotal(response.total);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load clients');
      } finally {
        setLoading(false);
      }
    };

    loadClients();
  }, [currentPage, pageSize, search]);

  const getCreditUsagePercent = (client: SalesClient) => {
    if (client.credit_limit === 0) return 0;
    return (client.credit_used / client.credit_limit) * 100;
  };

  const getCreditColor = (percent: number) => {
    if (percent < 50) return 'bg-green-50 text-green-700 border-green-200';
    if (percent < 80) return 'bg-yellow-50 text-yellow-700 border-yellow-200';
    return 'bg-red-50 text-red-700 border-red-200';
  };

  if (loading && clients.length === 0) {
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
          <h1 className="text-3xl font-bold text-gray-900">Sales Clients</h1>
          <p className="text-gray-600 mt-1">Manage client information and credit limits</p>
        </div>
        <Button onClick={() => navigate('/sales/clients/new')} size="lg">
          <Plus className="mr-2 h-4 w-4" />
          New Client
        </Button>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="pt-6">
          <Input
            placeholder="Search by name or code..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setCurrentPage(1);
            }}
          />
        </CardContent>
      </Card>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Clients Table */}
      <Card>
        <CardHeader>
          <CardTitle>Clients</CardTitle>
          <CardDescription>Showing {clients.length} of {total} clients</CardDescription>
        </CardHeader>
        <CardContent>
          {clients.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p>No clients found</p>
              <Button
                variant="link"
                onClick={() => navigate('/sales/clients/new')}
                className="mt-2"
              >
                Add First Client
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Code</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Name</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Email</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Credit Usage</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Status</th>
                    <th className="px-4 py-3 text-right font-semibold text-gray-700">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {clients.map((client) => {
                    const usagePercent = getCreditUsagePercent(client);
                    return (
                      <tr key={client.id} className="border-b hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium">{client.code}</td>
                        <td className="px-4 py-3">{client.name}</td>
                        <td className="px-4 py-3 text-gray-600">{client.email || '-'}</td>
                        <td className="px-4 py-3">
                          <div className={`inline-block px-3 py-1 rounded-full border text-sm ${getCreditColor(usagePercent)}`}>
                            <IndianRupee className="inline h-3 w-3 mr-1" />
                            {formatCurrency(client.credit_used)} / {formatCurrency(client.credit_limit)}
                            ({usagePercent.toFixed(0)}%)
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <Badge className={client.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                            {client.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-right space-x-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => navigate(`/sales/clients/${client.id}/edit`)}
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
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
