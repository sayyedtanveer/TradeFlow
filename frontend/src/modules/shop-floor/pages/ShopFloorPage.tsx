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
    <div className="min-h-screen bg-[#0d0f14] text-white">
      {/* Header — large touch-friendly on mobile */}
      <div className="border-b border-white/10 bg-[#111318] px-4 py-5 sm:px-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">🏭 Shop Floor</h1>
            <p className="text-xs text-slate-400 mt-1">Active production orders — tap to manage operations</p>
          </div>
          <button
            onClick={load}
            className="rounded-full p-2.5 bg-white/5 hover:bg-white/10 transition-colors"
            title="Refresh"
          >
            🔄
          </button>
        </div>
      </div>

      <div className="p-4 sm:p-6 space-y-3 max-w-2xl mx-auto">
        {loading && (
          <div className="flex flex-col items-center justify-center h-48 gap-3 text-slate-400">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm">Loading active orders…</span>
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-red-800 bg-red-900/20 p-4 text-sm text-red-300">
            {error}
          </div>
        )}

        {!loading && !error && orders.length === 0 && (
          <div className="flex flex-col items-center justify-center h-56 gap-4">
            <div className="text-5xl">✅</div>
            <p className="text-slate-400 text-sm font-medium">No IN_PROGRESS work orders</p>
            <p className="text-xs text-slate-500">All clear! Release and start a work order to see it here.</p>
            <button
              onClick={() => navigate('/work-orders')}
              className="mt-2 rounded-lg border border-white/10 px-4 py-2 text-xs text-slate-300 hover:bg-white/5 transition-colors"
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
              className="w-full text-left rounded-2xl border border-white/10 bg-[#111318] hover:bg-[#181c24] active:scale-[0.99] transition-all p-5 shadow-lg"
            >
              {/* Top row */}
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-lg font-bold text-indigo-300">{wo.wo_number}</span>
                    <span className="text-base">{PRIORITY_ICON[wo.priority]}</span>
                  </div>
                  <p className="text-xs text-slate-400">Due: <span className="text-slate-200">{wo.due_date}</span></p>
                </div>
                <span className="text-xs bg-amber-900 text-amber-200 rounded-full px-2.5 py-1 font-semibold shrink-0">
                  IN PROGRESS
                </span>
              </div>

              {/* Progress bar */}
              <div className="mt-4">
                <div className="flex justify-between text-xs text-slate-400 mb-1.5">
                  <span>Production Progress</span>
                  <span className="text-emerald-400 font-medium">{pct}%</span>
                </div>
                <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-indigo-600 to-emerald-500 transition-all duration-500"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-slate-500 mt-1">
                  <span>{Number(wo.produced_quantity).toFixed(3)} produced</span>
                  <span>{Number(wo.planned_quantity).toFixed(3)} planned</span>
                </div>
              </div>

              {/* CTA */}
              <div className="mt-4 text-right">
                <span className="text-xs text-indigo-400 font-medium">Manage operations →</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
