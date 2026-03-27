import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import workOrderService, { type CreateWorkOrderPayload } from '@/services/work-order.service';

const PRIORITIES = ['LOW', 'NORMAL', 'HIGH', 'URGENT'] as const;

const today = () => new Date().toISOString().split('T')[0];
const nextWeek = () => {
  const d = new Date();
  d.setDate(d.getDate() + 7);
  return d.toISOString().split('T')[0];
};

export default function WorkOrderCreatePage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<CreateWorkOrderPayload>({
    product_id: '',
    bom_id: '',
    planned_quantity: 1,
    start_date: today(),
    due_date: nextWeek(),
    priority: 'NORMAL',
    notes: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = <K extends keyof CreateWorkOrderPayload>(key: K, value: CreateWorkOrderPayload[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const payload: CreateWorkOrderPayload = {
        ...form,
        planned_quantity: Number(form.planned_quantity),
      };
      if (!payload.notes) delete payload.notes;
      if (!payload.sales_order_id) delete payload.sales_order_id;
      const res = await workOrderService.create(payload);
      navigate(`/work-orders/${res.data.id}`);
    } catch (e: any) {
      const detail = e?.response?.data?.message || e?.response?.data?.detail || 'Failed to create work order.';
      setError(detail);
    } finally {
      setSubmitting(false);
    }
  };

  const inputClass =
    'w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 transition-colors';

  return (
    <div className="min-h-screen bg-[#0d0f14] text-white">
      {/* Header */}
      <div className="border-b border-white/10 bg-[#111318] px-6 py-4">
        <button
          onClick={() => navigate('/work-orders')}
          className="text-slate-400 hover:text-white text-xs mb-2 block"
        >
          ← Work Orders
        </button>
        <h1 className="text-xl font-semibold tracking-tight">Create Work Order</h1>
        <p className="text-xs text-slate-400 mt-0.5">Start a new production work order from a BOM</p>
      </div>

      <div className="max-w-xl mx-auto p-6">
        {error && (
          <div className="mb-4 rounded-lg border border-red-800 bg-red-900/20 p-3 text-sm text-red-300">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Product ID */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">Product ID (Item Variant UUID) *</label>
            <input
              id="field-product-id"
              type="text"
              required
              placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
              value={form.product_id}
              onChange={(e) => set('product_id', e.target.value)}
              className={inputClass}
            />
          </div>

          {/* BOM ID */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">BOM ID *</label>
            <input
              id="field-bom-id"
              type="text"
              required
              placeholder="e.g. 550e8400-e29b-41d4-a716-446655440001"
              value={form.bom_id}
              onChange={(e) => set('bom_id', e.target.value)}
              className={inputClass}
            />
          </div>

          {/* Quantity */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">Planned Quantity *</label>
            <input
              id="field-planned-quantity"
              type="number"
              min="0.001"
              step="0.001"
              required
              value={form.planned_quantity}
              onChange={(e) => set('planned_quantity', Number(e.target.value) as any)}
              className={inputClass}
            />
          </div>

          {/* Dates */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Start Date *</label>
              <input
                id="field-start-date"
                type="date"
                required
                value={form.start_date}
                onChange={(e) => set('start_date', e.target.value)}
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Due Date *</label>
              <input
                id="field-due-date"
                type="date"
                required
                value={form.due_date}
                onChange={(e) => set('due_date', e.target.value)}
                className={inputClass}
              />
            </div>
          </div>

          {/* Priority */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">Priority</label>
            <div className="flex gap-2">
              {PRIORITIES.map((p) => (
                <button
                  type="button"
                  key={p}
                  onClick={() => set('priority', p)}
                  className={`flex-1 py-2 rounded-lg text-xs font-medium border transition-colors ${
                    form.priority === p
                      ? 'bg-indigo-600 border-indigo-600 text-white'
                      : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {/* Sales Order */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">Linked Sales Order ID (optional)</label>
            <input
              id="field-sales-order-id"
              type="text"
              placeholder="Leave blank if not linked"
              value={form.sales_order_id ?? ''}
              onChange={(e) => set('sales_order_id', e.target.value || undefined)}
              className={inputClass}
            />
          </div>

          {/* Notes */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">Notes</label>
            <textarea
              id="field-notes"
              rows={3}
              placeholder="Any production notes…"
              value={form.notes ?? ''}
              onChange={(e) => set('notes', e.target.value)}
              className={`${inputClass} resize-none`}
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={() => navigate('/work-orders')}
              className="flex-1 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 py-2.5 text-sm font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              id="btn-submit-work-order"
              type="submit"
              disabled={submitting}
              className="flex-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 py-2.5 text-sm font-medium transition-colors"
            >
              {submitting ? 'Creating…' : 'Create Work Order'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
