import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import workOrderService, { type WorkOrderSummary } from '@/services/work-order.service';

const PRIORITY_ICON: Record<string, string> = {
  LOW: '🔵',
  NORMAL: '🟢',
  HIGH: '🟡',
  URGENT: '🔴',
};

export default function ShopFloorPage() {
  const navigate = useNavigate();
  const [orders, setOrders] = useState<WorkOrderSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await workOrderService.list({ status: 'IN_PROGRESS' });
      setOrders(res.data);
    } catch {
      setError('Failed to load active work orders.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-6">
      {/* Header — large touch-friendly on mobile */}
      <div className="erp-surface px-5 py-5 sm:px-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-600">Execution</p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">Shop Floor</h1>
            <p className="mt-1 text-sm text-slate-500">Active production orders for operators and supervisors</p>
          </div>
          <button
            onClick={load}
            className="rounded-full border border-slate-200 bg-white p-2.5 text-slate-600 shadow-sm transition-colors hover:bg-slate-50 hover:text-slate-900"
            title="Refresh"
          >
            ↻
          </button>
        </div>
      </div>

      <div className="p-4 sm:p-6 space-y-3 max-w-2xl mx-auto">
        {loading && (
          <div className="flex h-48 flex-col items-center justify-center gap-3 rounded-2xl border border-slate-200 bg-white text-slate-500 shadow-sm">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm">Loading active orders...</span>
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {!loading && !error && orders.length === 0 && (
          <div className="flex h-56 flex-col items-center justify-center gap-4 rounded-2xl border border-dashed border-slate-200 bg-white shadow-sm">
            <div className="text-5xl">✅</div>
            <p className="text-sm font-medium text-slate-700">No in-progress work orders</p>
            <p className="text-xs text-slate-500">Release and start a work order to see it here.</p>
            <button
              onClick={() => navigate('/work-orders')}
              className="mt-2 rounded-xl border border-slate-200 px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 transition-colors"
            >
              View all work orders
            </button>
          </div>
        )}

        {!loading && orders.map((wo) => {
          const pct = wo.planned_quantity > 0
            ? Math.round((Number(wo.produced_quantity) / Number(wo.planned_quantity)) * 100)
            : 0;

          return (
            <button
              key={wo.id}
              id={`sf-wo-${wo.id}`}
              onClick={() => navigate(`${wo.id}/job-cards`)}
              className="w-full rounded-2xl border border-slate-200/80 bg-white p-5 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md active:scale-[0.99]"
            >
              {/* Top row */}
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-lg font-bold text-blue-700">{wo.wo_number}</span>
                    <span className="text-base">{PRIORITY_ICON[wo.priority]}</span>
                  </div>
                  <p className="text-xs text-slate-500">Due: <span className="text-slate-800">{wo.due_date}</span></p>
                </div>
                <span className="shrink-0 rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-700">
                  IN PROGRESS
                </span>
              </div>

              {/* Progress bar */}
              <div className="mt-4">
                <div className="mb-1.5 flex justify-between text-xs text-slate-500">
                  <span>Production Progress</span>
                  <span className="font-medium text-emerald-600">{pct}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-blue-600 to-emerald-500 transition-all duration-500"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <div className="mt-1 flex justify-between text-xs text-slate-500">
                  <span>{Number(wo.produced_quantity).toFixed(3)} produced</span>
                  <span>{Number(wo.planned_quantity).toFixed(3)} planned</span>
                </div>
              </div>

              {/* CTA */}
              <div className="mt-4 text-right">
                <span className="text-xs font-medium text-blue-600">Manage operations →</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
