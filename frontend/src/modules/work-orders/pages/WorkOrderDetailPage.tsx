import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { REALTIME_EVENT_NAME } from '@/components/notifications/RealtimeNotificationsBridge';
import workOrderService, {
  type WorkOrderDetail,
  type WorkOrderMaterial,
  type JobCard,
} from '@/services/work-order.service';
import { documentService } from '@/services/document.service';

const STATUS_COLORS: Record<string, string> = {
  PLANNED: 'bg-slate-100 text-slate-700',
  RELEASED: 'bg-blue-100 text-blue-700',
  MATERIAL_PENDING: 'bg-indigo-100 text-indigo-700',
  MATERIAL_RESERVED: 'bg-violet-100 text-violet-700',
  MATERIAL_ISSUED: 'bg-purple-100 text-purple-700',
  IN_PROGRESS: 'bg-amber-100 text-amber-700',
  IN_PRODUCTION: 'bg-amber-100 text-amber-700',
  QC_PENDING: 'bg-cyan-100 text-cyan-700',
  QC_APPROVED: 'bg-emerald-100 text-emerald-700',
  QC_REJECTED: 'bg-red-100 text-red-700',
  FG_RECEIVED: 'bg-teal-100 text-teal-700',
  COMPLETED: 'bg-emerald-100 text-emerald-700',
  CLOSED: 'bg-zinc-100 text-zinc-600',
  REWORK: 'bg-orange-100 text-orange-700',
  REJECTED: 'bg-red-100 text-red-700',
};

const JC_STATUS: Record<string, string> = {
  PENDING: 'bg-slate-100 text-slate-600',
  IN_PROGRESS: 'bg-amber-100 text-amber-700',
  DONE: 'bg-emerald-100 text-emerald-700',
};

// Lifecycle transitions allowed from the UI based on workflow ownership matrix
const ACTIONS: Record<string, Array<{ label: string; actionKey: string; color: string }>> = {
  PLANNED: [{ label: 'Release', actionKey: 'release', color: 'bg-blue-600 hover:bg-blue-500' }],
  RELEASED: [], // Auto-transitions to MATERIAL_PENDING
  MATERIAL_PENDING: [], // Auto-transitions based on material reservation
  MATERIAL_RESERVED: [{ label: 'Issue Material', actionKey: 'issue', color: 'bg-violet-600 hover:bg-violet-500' }],
  MATERIAL_ISSUED: [{ label: 'Start Production', actionKey: 'start', color: 'bg-purple-600 hover:bg-purple-500' }],
  IN_PRODUCTION: [{ label: 'Complete Production', actionKey: 'complete', color: 'bg-amber-600 hover:bg-amber-500' }],
  QC_PENDING: [], // Handled by QC dashboard
  QC_APPROVED: [{ label: 'Receive FG', actionKey: 'receive-fg', color: 'bg-emerald-600 hover:bg-emerald-500' }],
  QC_REJECTED: [
    { label: 'Send to Rework', actionKey: 'rework', color: 'bg-orange-600 hover:bg-orange-500' },
    { label: 'Scrap', actionKey: 'scrap', color: 'bg-red-600 hover:bg-red-500' }
  ],
  FG_RECEIVED: [{ label: 'Complete', actionKey: 'complete', color: 'bg-teal-600 hover:bg-teal-500' }],
  COMPLETED: [{ label: 'Close', actionKey: 'close', color: 'bg-emerald-600 hover:bg-emerald-500' }],
  CLOSED: [],
  REWORK: [{ label: 'Complete Rework', actionKey: 'complete', color: 'bg-orange-600 hover:bg-orange-500' }],
  REJECTED: [{ label: 'Close', actionKey: 'close', color: 'bg-red-600 hover:bg-red-500' }],
};

export default function WorkOrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [wo, setWo] = useState<WorkOrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionPending, setActionPending] = useState(false);
  const [productionPending, setProductionPending] = useState(false);
  const [tab, setTab] = useState<'materials' | 'job-cards'>('materials');
  const [productionDraft, setProductionDraft] = useState({
    produced_quantity: '',
    scrap_quantity: '0',
    notes: '',
  });
  const [documentLoading, setDocumentLoading] = useState(false);

  const load = useCallback(async (silent = false) => {
    if (!id) return;
    if (!silent) setLoading(true);
    setError(null);
    try {
      const res = await workOrderService.get(id);
      setWo(res.data);
    } catch {
      setError('Failed to load work order.');
    } finally {
      if (!silent) setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const handleRealtime = () => {
      void load(true);
    };
    window.addEventListener(REALTIME_EVENT_NAME, handleRealtime);
    return () => window.removeEventListener(REALTIME_EVENT_NAME, handleRealtime);
  }, [load]);

  const handleAction = async (actionKey: string) => {
    if (!id || actionPending) return;
    setActionPending(true);
    try {
      if (actionKey === 'release') await workOrderService.release(id);
      else if (actionKey === 'start') await workOrderService.start(id);
      else if (actionKey === 'complete') await workOrderService.complete(id);
      else if (actionKey === 'close') await workOrderService.close(id);
      else if (actionKey === 'issue') {
        // Material issue - will be handled by storekeeper dashboard
        setError('Material issue is handled by the Storekeeper Dashboard.');
      }
      else if (actionKey === 'receive-fg') {
        // FG receive - will be handled automatically after QC approval
        setError('FG receipt is automatic after QC approval.');
      }
      else if (actionKey === 'rework') {
        // Rework - will be handled by QC dashboard
        setError('Rework is handled by the QC Dashboard.');
      }
      else if (actionKey === 'scrap') {
        // Scrap - will be handled by planner dashboard
        setError('Scrap decisions are handled by the Planner Dashboard.');
      }
      await load();
    } catch (e: any) {
      const msg = e?.response?.data?.error_code === 'MATERIAL_NOT_ISSUED'
        ? 'Record production before completing this work order.'
        : e?.response?.data?.message || 'Action failed.';
      setError(msg);
    } finally {
      setActionPending(false);
    }
  };

  const handleRecordProduction = async () => {
    if (!id || productionPending) return;

    const producedQuantity = Number(productionDraft.produced_quantity);
    const scrapQuantity = Number(productionDraft.scrap_quantity || 0);

    if (!Number.isFinite(producedQuantity) || producedQuantity <= 0) {
      setError('Enter a produced quantity greater than zero before saving production.');
      return;
    }

    if (!Number.isFinite(scrapQuantity) || scrapQuantity < 0) {
      setError('Scrap quantity cannot be negative.');
      return;
    }

    setProductionPending(true);
    setError(null);
    try {
      await workOrderService.recordProduction(id, {
        produced_quantity: producedQuantity,
        scrap_quantity: scrapQuantity,
        notes: productionDraft.notes.trim() || undefined,
      });
      setProductionDraft({
        produced_quantity: '',
        scrap_quantity: '0',
        notes: '',
      });
      await load();
    } catch (e: any) {
      const msg = e?.response?.data?.message || 'Failed to record production.';
      setError(msg);
    } finally {
      setProductionPending(false);
    }
  };

  const handleDownloadPDF = async () => {
    if (!id || documentLoading) return;
    setDocumentLoading(true);
    setError(null);
    try {
      // Generate document
      const document = await documentService.generateDocument('work_order', id);
      // Download the PDF
      await documentService.downloadDocumentByUrl(document.id, `WO-${wo?.wo_number}.pdf`);
    } catch (e: any) {
      const msg = e?.response?.data?.message || 'Failed to generate PDF.';
      setError(msg);
    } finally {
      setDocumentLoading(false);
    }
  };

  const handlePrintPDF = async () => {
    if (!id || documentLoading) return;
    setDocumentLoading(true);
    setError(null);
    try {
      // Generate document
      const document = await documentService.generateDocument('work_order', id);
      // Get preview URL
      const previewUrl = await documentService.previewDocument(document.id);
      // Open in new window for printing
      const printWindow = window.open(previewUrl, '_blank');
      if (printWindow) {
        printWindow.onload = () => {
          printWindow.print();
        };
      }
    } catch (e: any) {
      const msg = e?.response?.data?.message || 'Failed to generate PDF for printing.';
      setError(msg);
    } finally {
      setDocumentLoading(false);
    }
  };

  if (loading) return (
    <div className="flex h-64 items-center justify-center rounded-2xl border border-slate-200 bg-white text-sm text-slate-500 shadow-sm animate-pulse">
      Loading…
    </div>
  );

  if (!wo) return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      {error || 'Work order not found.'}
    </div>
  );

  const actions = (ACTIONS[wo.status] ?? []).map((action) =>
    action.actionKey === 'complete'
      ? { ...action, disabled: Number(wo.produced_quantity) <= 0 }
      : { ...action, disabled: false }
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="erp-surface px-5 py-5 sm:px-6">
        <div className="flex items-center gap-3 mb-1">
          <button onClick={() => navigate('/work-orders')} className="text-xs font-medium text-slate-500 hover:text-slate-900">
            Back to Work Orders
          </button>
        </div>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-600">Manufacturing execution</p>
            <h1 className="mt-2 text-2xl font-semibold font-mono text-slate-900">{wo.wo_number}</h1>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_COLORS[wo.status]}`}>
                {wo.status.replace('_', ' ')}
              </span>
              <span className="text-xs text-slate-500">Priority: <span className="text-slate-800">{wo.priority}</span></span>
              <span className="text-xs text-slate-500">Due: <span className="text-slate-800">{wo.due_date}</span></span>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handlePrintPDF}
              disabled={documentLoading}
              className="rounded-lg px-4 py-2 text-sm font-medium bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 transition-colors disabled:cursor-not-allowed disabled:opacity-50"
            >
              {documentLoading ? '…' : 'Print'}
            </button>
            <button
              onClick={handleDownloadPDF}
              disabled={documentLoading}
              className="rounded-lg px-4 py-2 text-sm font-medium bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 transition-colors disabled:cursor-not-allowed disabled:opacity-50"
            >
              {documentLoading ? '…' : 'Download PDF'}
            </button>
            {actions.map((a) => (
              <button
                key={a.actionKey}
                id={`btn-wo-${a.actionKey}`}
                onClick={() => handleAction(a.actionKey)}
                disabled={actionPending || a.disabled}
                title={a.disabled ? 'Record production before completing this work order.' : undefined}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${a.color}`}
              >
                {actionPending ? '…' : a.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div>
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: 'Planned Qty', value: Number(wo.planned_quantity).toFixed(3), color: 'text-slate-900' },
          { label: 'Produced', value: Number(wo.produced_quantity).toFixed(3), color: 'text-emerald-600' },
          { label: 'Scrap', value: Number(wo.scrap_quantity).toFixed(3), color: 'text-red-600' },
          { label: 'Completion', value: wo.planned_quantity > 0 ? `${Math.round((Number(wo.produced_quantity) / Number(wo.planned_quantity)) * 100)}%` : '0%', color: 'text-blue-600' },
        ].map((c) => (
          <div key={c.label} className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{c.label}</p>
            <p className={`text-2xl font-semibold mt-1 tabular-nums ${c.color}`}>{c.value}</p>
          </div>
        ))}
      </div>

      {(wo.status === 'RELEASED' || wo.status === 'IN_PRODUCTION') && (
        <div>
          <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <h2 className="text-sm font-semibold text-slate-900">Record Production</h2>
                <p className="mt-1 text-xs text-slate-500">
                  Complete becomes available after at least one production entry is recorded.
                </p>
              </div>
              {wo.status === 'RELEASED' && (
                <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs text-amber-700">
                  Start the work order before recording output
                </span>
              )}
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div>
                <label className="mb-1 block text-xs uppercase tracking-wide text-slate-400">Produced Qty</label>
                <input
                  id="wo-produced-quantity"
                  type="number"
                  min="0.001"
                  step="0.001"
                  value={productionDraft.produced_quantity}
                  onChange={(event) =>
                    setProductionDraft((current) => ({
                      ...current,
                      produced_quantity: event.target.value,
                    }))
                  }
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none placeholder:text-slate-400"
                  placeholder="Enter produced quantity"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs uppercase tracking-wide text-slate-400">Scrap Qty</label>
                <input
                  id="wo-scrap-quantity"
                  type="number"
                  min="0"
                  step="0.001"
                  value={productionDraft.scrap_quantity}
                  onChange={(event) =>
                    setProductionDraft((current) => ({
                      ...current,
                      scrap_quantity: event.target.value,
                    }))
                  }
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none placeholder:text-slate-400"
                />
              </div>
              <div className="flex items-end">
                <button
                  id="btn-record-production"
                  onClick={handleRecordProduction}
                  disabled={productionPending || wo.status !== 'IN_PRODUCTION'}
                  className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-blue-700 px-4 py-2 text-sm font-medium text-white shadow-sm transition-all hover:-translate-y-0.5 hover:from-blue-700 hover:to-blue-800 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {productionPending ? 'Savingâ€¦' : 'Record Production'}
                </button>
              </div>
              <div className="md:col-span-3">
                <label className="mb-1 block text-xs uppercase tracking-wide text-slate-400">Notes</label>
                <textarea
                  id="wo-production-notes"
                  value={productionDraft.notes}
                  onChange={(event) =>
                    setProductionDraft((current) => ({
                      ...current,
                      notes: event.target.value,
                    }))
                  }
                  rows={3}
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none placeholder:text-slate-400"
                  placeholder="Optional production notes"
                />
              </div>
            </div>

            {wo.status === 'IN_PRODUCTION' && Number(wo.produced_quantity) <= 0 && (
              <p className="mt-3 text-xs text-amber-700">
                Next step: record produced quantity, then complete the work order.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div>
        <div className="flex gap-1 border-b border-slate-200">
          {(['materials', 'job-cards'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                tab === t ? 'border-b-2 border-blue-600 text-slate-900' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              {t === 'materials' ? 'Materials' : 'Job Cards'}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="pt-1">
        {tab === 'materials' && (
          <div className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm">
            {wo.materials.length === 0 ? (
              <p className="p-6 text-center text-sm text-slate-500">No materials attached.</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-[0.18em] text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Material Code</th>
                    <th className="px-4 py-3">Required</th>
                    <th className="px-4 py-3">Issued</th>
                    <th className="px-4 py-3">Remaining</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {wo.materials.map((m: WorkOrderMaterial) => {
                    const remaining = Number(m.required_quantity) - Number(m.issued_quantity);
                    const fullyIssued = remaining <= 0;
                    return (
                      <tr key={m.id}>
                        <td className="px-4 py-3">
                          <div className="font-mono text-xs text-slate-900">{m.material_code}</div>
                          <div className="text-xs text-slate-500">{m.material_name}</div>
                        </td>
                        <td className="px-4 py-3 tabular-nums">{Number(m.required_quantity).toFixed(3)}</td>
                        <td className="px-4 py-3 tabular-nums text-emerald-600">{Number(m.issued_quantity).toFixed(3)}</td>
                        <td className={`px-4 py-3 tabular-nums ${remaining > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
                          {remaining.toFixed(3)}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`rounded-full px-2 py-0.5 text-xs ${fullyIssued ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
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
              <p className="py-8 text-center text-sm text-slate-500">No job cards attached.</p>
            ) : (
              wo.job_cards.map((jc: JobCard) => (
                <div key={jc.id} className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm flex items-center justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-slate-100 text-sm font-bold text-slate-600">
                      {jc.sequence}
                    </span>
                    <div>
                      <p className="font-mono text-sm font-medium text-slate-900">OP-{jc.sequence} {jc.operation_name}</p>
                      {jc.started_at && (
                        <p className="text-xs text-slate-500">
                          Started: {new Date(jc.started_at).toLocaleString()}
                        </p>
                      )}
                      {jc.completed_at && (
                        <p className="text-xs text-emerald-600">
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
            {wo.status === 'IN_PRODUCTION' && (
              <p className="mt-2 text-center text-xs text-slate-500">
                Go to <button onClick={() => navigate(`/shop-floor/${id}/job-cards`)} className="font-medium text-blue-600 hover:underline">Shop Floor</button> to start or complete individual operations.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
