import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import workOrderService, {
  type WorkOrderDetail,
  type WorkOrderMaterial,
  type JobCard,
} from '@/services/work-order.service';

const STATUS_COLORS: Record<string, string> = {
  PLANNED: 'bg-slate-700 text-slate-200',
  RELEASED: 'bg-blue-900 text-blue-200',
  IN_PROGRESS: 'bg-amber-900 text-amber-200',
  COMPLETED: 'bg-emerald-900 text-emerald-200',
  CLOSED: 'bg-zinc-700 text-zinc-300',
};

const JC_STATUS: Record<string, string> = {
  PENDING: 'bg-slate-700 text-slate-300',
  IN_PROGRESS: 'bg-amber-900 text-amber-200',
  DONE: 'bg-emerald-900 text-emerald-200',
};

// Lifecycle transitions allowed from the UI
const ACTIONS: Record<string, Array<{ label: string; actionKey: string; color: string }>> = {
  PLANNED: [{ label: 'Release', actionKey: 'release', color: 'bg-blue-600 hover:bg-blue-500' }],
  RELEASED: [{ label: 'Start', actionKey: 'start', color: 'bg-amber-600 hover:bg-amber-500' }],
  IN_PROGRESS: [{ label: 'Complete', actionKey: 'complete', color: 'bg-emerald-600 hover:bg-emerald-500' }],
  COMPLETED: [{ label: 'Close', actionKey: 'close', color: 'bg-zinc-600 hover:bg-zinc-500' }],
  CLOSED: [],
};

export default function WorkOrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [wo, setWo] = useState<WorkOrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionPending, setActionPending] = useState(false);
  const [tab, setTab] = useState<'materials' | 'job-cards'>('materials');

  const load = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await workOrderService.get(id);
      setWo(res.data);
    } catch {
      setError('Failed to load work order.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [id]);

  const handleAction = async (actionKey: string) => {
    if (!id || actionPending) return;
    setActionPending(true);
    try {
      if (actionKey === 'release') await workOrderService.release(id);
      else if (actionKey === 'start') await workOrderService.start(id);
      else if (actionKey === 'complete') await workOrderService.complete(id);
      else if (actionKey === 'close') await workOrderService.close(id);
      await load();
    } catch (e: any) {
      const msg = e?.response?.data?.message || 'Action failed.';
      setError(msg);
    } finally {
      setActionPending(false);
    }
  };

  if (loading) return (
    <div className="flex h-64 items-center justify-center text-slate-400 text-sm animate-pulse bg-[#0d0f14]">
      Loading…
    </div>
  );

  if (error || !wo) return (
    <div className="m-6 rounded-lg border border-red-800 bg-red-900/20 p-4 text-sm text-red-300 bg-[#0d0f14]">
      {error || 'Work order not found.'}
    </div>
  );

  const actions = ACTIONS[wo.status] ?? [];

  return (
    <div className="min-h-screen bg-[#0d0f14] text-white">
      {/* Header */}
      <div className="border-b border-white/10 bg-[#111318] px-6 py-4">
        <div className="flex items-center gap-3 mb-1">
          <button onClick={() => navigate('/work-orders')} className="text-slate-400 hover:text-white text-xs">
            ← Work Orders
          </button>
        </div>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-xl font-semibold font-mono text-indigo-300">{wo.wo_number}</h1>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_COLORS[wo.status]}`}>
                {wo.status.replace('_', ' ')}
              </span>
              <span className="text-xs text-slate-400">Priority: <span className="text-slate-200">{wo.priority}</span></span>
              <span className="text-xs text-slate-400">Due: <span className="text-slate-200">{wo.due_date}</span></span>
            </div>
          </div>
          <div className="flex gap-2">
            {actions.map((a) => (
              <button
                key={a.actionKey}
                id={`btn-wo-${a.actionKey}`}
                onClick={() => handleAction(a.actionKey)}
                disabled={actionPending}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 ${a.color}`}
              >
                {actionPending ? '…' : a.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-6">
        {[
          { label: 'Planned Qty', value: Number(wo.planned_quantity).toFixed(3), color: 'text-white' },
          { label: 'Produced', value: Number(wo.produced_quantity).toFixed(3), color: 'text-emerald-400' },
          { label: 'Scrap', value: Number(wo.scrap_quantity).toFixed(3), color: 'text-red-400' },
          { label: 'Completion', value: wo.planned_quantity > 0 ? `${Math.round((Number(wo.produced_quantity) / Number(wo.planned_quantity)) * 100)}%` : '0%', color: 'text-indigo-300' },
        ].map((c) => (
          <div key={c.label} className="rounded-xl border border-white/10 bg-[#111318] p-4">
            <p className="text-xs text-slate-400">{c.label}</p>
            <p className={`text-2xl font-semibold mt-1 tabular-nums ${c.color}`}>{c.value}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="px-6">
        <div className="flex gap-1 border-b border-white/10">
          {(['materials', 'job-cards'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                tab === t ? 'border-b-2 border-indigo-500 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              {t === 'materials' ? 'Materials' : 'Job Cards'}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="p-6 pt-4">
        {tab === 'materials' && (
          <div className="overflow-hidden rounded-xl border border-white/10">
            {wo.materials.length === 0 ? (
              <p className="p-6 text-sm text-slate-400 text-center">No materials attached.</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-white/5 text-xs text-slate-400 uppercase tracking-wide text-left">
                  <tr>
                    <th className="px-4 py-3">Material ID</th>
                    <th className="px-4 py-3">Required</th>
                    <th className="px-4 py-3">Issued</th>
                    <th className="px-4 py-3">Remaining</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {wo.materials.map((m: WorkOrderMaterial) => {
                    const remaining = Number(m.required_quantity) - Number(m.issued_quantity);
                    const fullyIssued = remaining <= 0;
                    return (
                      <tr key={m.id}>
                        <td className="px-4 py-3 font-mono text-xs text-slate-300">{m.material_id.slice(0, 8)}…</td>
                        <td className="px-4 py-3 tabular-nums">{Number(m.required_quantity).toFixed(3)}</td>
                        <td className="px-4 py-3 tabular-nums text-emerald-400">{Number(m.issued_quantity).toFixed(3)}</td>
                        <td className={`px-4 py-3 tabular-nums ${remaining > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                          {remaining.toFixed(3)}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`rounded-full px-2 py-0.5 text-xs ${fullyIssued ? 'bg-emerald-900 text-emerald-200' : 'bg-amber-900/60 text-amber-300'}`}>
                            {fullyIssued ? 'Fully Issued' : 'Pending'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}

        {tab === 'job-cards' && (
          <div className="space-y-3">
            {wo.job_cards.length === 0 ? (
              <p className="text-sm text-slate-400 text-center py-8">No job cards attached.</p>
            ) : (
              wo.job_cards.map((jc: JobCard) => (
                <div key={jc.id} className="rounded-xl border border-white/10 bg-[#111318] p-4 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <span className="flex-shrink-0 w-8 h-8 rounded-full bg-white/10 text-slate-300 text-sm font-bold flex items-center justify-center">
                      {jc.sequence}
                    </span>
                    <div>
                      <p className="text-sm font-medium text-white font-mono">{jc.operation_id.slice(0, 8)}…</p>
                      {jc.started_at && (
                        <p className="text-xs text-slate-400">
                          Started: {new Date(jc.started_at).toLocaleString()}
                        </p>
                      )}
                      {jc.completed_at && (
                        <p className="text-xs text-emerald-400">
                          Done: {new Date(jc.completed_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                  </div>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold shrink-0 ${JC_STATUS[jc.status]}`}>
                    {jc.status.replace('_', ' ')}
                  </span>
                </div>
              ))
            )}
            {wo.status === 'IN_PROGRESS' && (
              <p className="text-xs text-center text-slate-400 mt-2">
                Go to <button onClick={() => navigate(`/shop-floor/${id}/job-cards`)} className="text-indigo-400 hover:underline">Shop Floor</button> to start/complete individual operations.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
