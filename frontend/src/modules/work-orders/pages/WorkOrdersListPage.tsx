import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import workOrderService, { type WorkOrderSummary } from '@/services/work-order.service';

const STATUS_COLORS: Record<string, string> = {
  PLANNED: 'bg-slate-700 text-slate-200',
  RELEASED: 'bg-blue-900 text-blue-200',
  IN_PROGRESS: 'bg-amber-900 text-amber-200',
  COMPLETED: 'bg-emerald-900 text-emerald-200',
  CLOSED: 'bg-zinc-700 text-zinc-300',
};

const PRIORITY_COLORS: Record<string, string> = {
  LOW: 'text-slate-400',
  NORMAL: 'text-slate-200',
  HIGH: 'text-amber-400',
  URGENT: 'text-red-400',
};

const STATUS_OPTIONS = ['', 'PLANNED', 'RELEASED', 'IN_PROGRESS', 'COMPLETED', 'CLOSED'];

export default function WorkOrdersListPage() {
  const navigate = useNavigate();
  const [orders, setOrders] = useState<WorkOrderSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await workOrderService.list(statusFilter ? { status: statusFilter } : undefined);
      setOrders(res.data);
    } catch {
      setError('Failed to load work orders.');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="min-h-screen bg-[#0d0f14] text-white">
      {/* Header */}
      <div className="border-b border-white/10 bg-[#111318] px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Work Orders</h1>
          <p className="text-xs text-slate-400 mt-0.5">Manufacturing execution management</p>
        </div>
        <button
          id="btn-create-work-order"
          onClick={() => navigate('new')}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 py-2 text-sm font-medium transition-colors"
        >
          <span className="text-lg leading-none">+</span> New Work Order
        </button>
      </div>

      {/* Filters */}
      <div className="px-6 py-3 flex items-center gap-3 border-b border-white/5">
        <span className="text-xs text-slate-400">Filter by status:</span>
        <div className="flex gap-2 flex-wrap">
          {STATUS_OPTIONS.map((s) => (
            <button
              key={s || 'ALL'}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                statusFilter === s
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white/5 text-slate-300 hover:bg-white/10'
              }`}
            >
              {s || 'All'}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {loading && (
          <div className="flex items-center justify-center h-40 text-slate-400 text-sm animate-pulse">
            Loading work orders…
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-red-800 bg-red-900/20 p-4 text-sm text-red-300">
            {error}
          </div>
        )}

        {!loading && !error && orders.length === 0 && (
          <div className="flex flex-col items-center justify-center h-48 gap-3">
            <div className="text-4xl">📋</div>
            <p className="text-slate-400 text-sm">No work orders found.</p>
            <button
              onClick={() => navigate('new')}
              className="text-xs text-indigo-400 hover:underline"
            >
              Create your first work order
            </button>
          </div>
        )}

        {!loading && orders.length > 0 && (
          <div className="overflow-hidden rounded-xl border border-white/10">
            <table className="w-full text-sm">
              <thead className="bg-white/5 text-left text-xs text-slate-400 uppercase tracking-wide">
                <tr>
                  <th className="px-4 py-3">WO #</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Priority</th>
                  <th className="px-4 py-3">Qty Planned</th>
                  <th className="px-4 py-3">Qty Produced</th>
                  <th className="px-4 py-3">Due Date</th>
                  <th className="px-4 py-3">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {orders.map((wo) => (
                  <tr
                    key={wo.id}
                    onClick={() => navigate(wo.id)}
                    className="cursor-pointer hover:bg-white/3 transition-colors"
                  >
                    <td className="px-4 py-3 font-mono text-indigo-300 font-medium">{wo.wo_number}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_COLORS[wo.status]}`}>
                        {wo.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className={`px-4 py-3 text-xs font-medium ${PRIORITY_COLORS[wo.priority]}`}>
                      {wo.priority}
                    </td>
                    <td className="px-4 py-3 tabular-nums">{Number(wo.planned_quantity).toFixed(3)}</td>
                    <td className="px-4 py-3 tabular-nums text-emerald-400">{Number(wo.produced_quantity).toFixed(3)}</td>
                    <td className="px-4 py-3 text-slate-300">{wo.due_date}</td>
                    <td className="px-4 py-3 text-slate-400 text-xs">
                      {new Date(wo.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
