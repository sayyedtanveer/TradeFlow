import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Loader2, PackageSearch, ShoppingCart } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { bomService } from '@/services/bom.service';
import { productService } from '@/services/product.service';
import workOrderService, {
  type CreateWorkOrderPayload,
  type MaterialAvailabilityPreview,
} from '@/services/work-order.service';
import type { BOM, ItemVariantSearchItem } from '@/types/bom.types';

const PRIORITIES = ['LOW', 'NORMAL', 'HIGH', 'URGENT'] as const;

const today = () => new Date().toISOString().split('T')[0];
const nextWeek = () => {
  const value = new Date();
  value.setDate(value.getDate() + 7);
  return value.toISOString().split('T')[0];
};

const formatQuantity = (value: number, unitCode?: string | null) => {
  const formatted = Number(value ?? 0).toLocaleString(undefined, {
    maximumFractionDigits: 3,
  });
  return unitCode ? `${formatted} ${unitCode}` : formatted;
};

const STATUS_STYLES: Record<'ok' | 'low' | 'shortage', string> = {
  ok: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  low: 'bg-amber-50 text-amber-700 border-amber-200',
  shortage: 'bg-rose-50 text-rose-700 border-rose-200',
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
  const [variantSearch, setVariantSearch] = useState('');
  const [variants, setVariants] = useState<ItemVariantSearchItem[]>([]);
  const [selectedVariant, setSelectedVariant] = useState<ItemVariantSearchItem | null>(null);
  const [variantsLoading, setVariantsLoading] = useState(false);
  const [variantError, setVariantError] = useState<string | null>(null);
  const [boms, setBoms] = useState<BOM[]>([]);
  const [bomsLoading, setBomsLoading] = useState(false);
  const [availability, setAvailability] = useState<MaterialAvailabilityPreview | null>(null);
  const [availabilityLoading, setAvailabilityLoading] = useState(false);
  const [availabilityError, setAvailabilityError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [shortageDialogOpen, setShortageDialogOpen] = useState(false);

  const setField = <K extends keyof CreateWorkOrderPayload>(
    key: K,
    value: CreateWorkOrderPayload[K],
  ) => setForm((current) => ({ ...current, [key]: value }));

  useEffect(() => {
    let cancelled = false;
    const timeoutId = window.setTimeout(async () => {
      setVariantsLoading(true);
      setVariantError(null);
      try {
        const response = await productService.searchVariants({
          search: variantSearch.trim() || undefined,
          is_active: true,
          page_size: 50,
        });
        if (cancelled) {
          return;
        }
        setVariants(response.items);
        if (form.product_id) {
          const match = response.items.find((item) => item.id === form.product_id);
          if (match) {
            setSelectedVariant(match);
          }
        }
      } catch (requestError: any) {
        if (!cancelled) {
          setVariantError(requestError?.message || 'Unable to load finished goods.');
        }
      } finally {
        if (!cancelled) {
          setVariantsLoading(false);
        }
      }
    }, 250);

    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [form.product_id, variantSearch]);

  useEffect(() => {
    if (!form.product_id) {
      setBoms([]);
      setAvailability(null);
      setAvailabilityError(null);
      return;
    }

    let cancelled = false;
    setBomsLoading(true);
    setAvailability(null);
    setAvailabilityError(null);

    bomService
      .getBOMsForProduct(form.product_id, false, { page_size: 20 })
      .then((response) => {
        if (cancelled) {
          return;
        }
        setBoms(response.items);
        const preferredBom =
          response.items.find((item) => item.id === form.bom_id) ??
          response.items.find((item) => item.is_active) ??
          response.items[0];
        setForm((current) => ({
          ...current,
          bom_id: preferredBom?.id ?? '',
        }));
      })
      .catch((requestError: any) => {
        if (!cancelled) {
          setBoms([]);
          setForm((current) => ({ ...current, bom_id: '' }));
          setAvailabilityError(requestError?.message || 'Unable to load BOMs for this product.');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setBomsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [form.bom_id, form.product_id]);

  useEffect(() => {
    if (!form.product_id || !form.bom_id || Number(form.planned_quantity) <= 0) {
      setAvailability(null);
      return;
    }

    let cancelled = false;
    setAvailabilityLoading(true);
    setAvailabilityError(null);

    workOrderService
      .checkMaterialAvailability({
        product_id: form.product_id,
        bom_id: form.bom_id,
        quantity: Number(form.planned_quantity),
      })
      .then((response) => {
        if (!cancelled) {
          setAvailability(response.data);
        }
      })
      .catch((requestError: any) => {
        if (!cancelled) {
          setAvailability(null);
          setAvailabilityError(
            requestError?.message || 'Unable to compare BOM requirements with inventory.',
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setAvailabilityLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [form.bom_id, form.planned_quantity, form.product_id]);

  const createWorkOrder = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const payload: CreateWorkOrderPayload = {
        ...form,
        planned_quantity: Number(form.planned_quantity),
      };
      if (!payload.notes) {
        delete payload.notes;
      }
      if (!payload.sales_order_id) {
        delete payload.sales_order_id;
      }
      const response = await workOrderService.create(payload);
      navigate(`/work-orders/${response.data.id}`);
    } catch (requestError: any) {
      setError(requestError?.message || 'Failed to create work order.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleProductChange = (productId: string) => {
    const match = variants.find((item) => item.id === productId) ?? selectedVariant;
    setSelectedVariant(match?.id === productId ? match : null);
    setForm((current) => ({
      ...current,
      product_id: productId,
      bom_id: '',
    }));
    setAvailability(null);
    setAvailabilityError(null);
    setError(null);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);

    if (!form.product_id) {
      setError('Choose a finished good before creating the work order.');
      return;
    }

    if (!form.bom_id) {
      setError('Choose a BOM for the selected finished good.');
      return;
    }

    if (availabilityLoading) {
      setError('Material availability is still loading. Please wait a moment and try again.');
      return;
    }

    if (availability?.has_shortage) {
      setShortageDialogOpen(true);
      return;
    }

    await createWorkOrder();
  };

  const shortageLines = availability?.lines.filter((line) => line.shortage_quantity > 0) ?? [];
  const visibleVariants =
    selectedVariant && !variants.some((item) => item.id === selectedVariant.id)
      ? [selectedVariant, ...variants]
      : variants;
  const selectedBom = boms.find((item) => item.id === form.bom_id) ?? null;

  return (
    <div className="space-y-6 pb-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <button
            onClick={() => navigate('/work-orders')}
            className="mb-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            Back to work orders
          </button>
          <h1 className="text-2xl font-semibold tracking-tight">Create Work Order</h1>
          <p className="text-sm text-muted-foreground">
            Pick a finished good, review its raw-material requirement, then create the production job.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={() => navigate('/products')}>
            Finished Goods
          </Button>
          <Button variant="outline" size="sm" onClick={() => navigate('/inventory/materials')}>
            Raw Materials
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <div className="space-y-6">
          <section className="rounded-2xl border bg-card p-6 shadow-sm">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold">Finished Good</h2>
                <p className="text-sm text-muted-foreground">
                  Search active variants instead of pasting product and BOM UUIDs.
                </p>
              </div>
              <div className="rounded-full bg-muted px-3 py-1 text-xs text-muted-foreground">
                Production input
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label htmlFor="variant-search" className="text-sm font-medium">
                  Search finished goods
                </label>
                <input
                  id="variant-search"
                  type="text"
                  value={variantSearch}
                  onChange={(event) => setVariantSearch(event.target.value)}
                  placeholder="Search by product code or name"
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                />
                {variantError && <p className="text-xs text-rose-600">{variantError}</p>}
              </div>

              <div className="space-y-2">
                <label htmlFor="field-product-id" className="text-sm font-medium">
                  Finished good variant
                </label>
                <select
                  id="field-product-id"
                  required
                  value={form.product_id}
                  onChange={(event) => handleProductChange(event.target.value)}
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                >
                  <option value="">Select a finished good</option>
                  {visibleVariants.map((variant) => (
                    <option key={variant.id} value={variant.id}>
                      {variant.code} - {variant.name}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-muted-foreground">
                  {variantsLoading ? 'Refreshing products...' : `${visibleVariants.length} products ready for planning.`}
                </p>
              </div>
            </div>

            {selectedVariant && (
              <div className="mt-4 rounded-xl border bg-muted/40 p-4">
                <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="font-medium">{selectedVariant.name}</p>
                    <p className="text-sm text-muted-foreground">{selectedVariant.code}</p>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Base unit: {selectedVariant.base_unit_code || 'Not mapped'}
                  </div>
                </div>
              </div>
            )}
          </section>

          <section className="rounded-2xl border bg-card p-6 shadow-sm">
            <div className="mb-4">
              <h2 className="text-lg font-semibold">Work Order Details</h2>
              <p className="text-sm text-muted-foreground">
                Choose the BOM version and enter schedule details for this production run.
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label htmlFor="field-bom-id" className="text-sm font-medium">
                  BOM version
                </label>
                <select
                  id="field-bom-id"
                  required
                  value={form.bom_id}
                  onChange={(event) => setField('bom_id', event.target.value)}
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                  disabled={!form.product_id || bomsLoading}
                >
                  <option value="">{bomsLoading ? 'Loading BOMs...' : 'Select a BOM'}</option>
                  {boms.map((bom) => (
                    <option key={bom.id} value={bom.id}>
                      {bom.version} {bom.is_active ? '(Active)' : '(Draft)'}
                    </option>
                  ))}
                </select>
                {selectedBom && (
                  <p className="text-xs text-muted-foreground">
                    {selectedBom.lines.length} component lines in this BOM.
                  </p>
                )}
                {!bomsLoading && form.product_id && boms.length === 0 && (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                    No BOM found for this finished good. Create one before releasing the work order.
                    <div className="mt-2">
                      <Button type="button" variant="outline" size="sm" onClick={() => navigate('/bom/new')}>
                        Create BOM
                      </Button>
                    </div>
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <label htmlFor="field-planned-quantity" className="text-sm font-medium">
                  Planned quantity
                </label>
                <input
                  id="field-planned-quantity"
                  type="number"
                  min="0.001"
                  step="0.001"
                  required
                  value={form.planned_quantity}
                  onChange={(event) => setField('planned_quantity', Number(event.target.value))}
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="field-start-date" className="text-sm font-medium">
                  Start date
                </label>
                <input
                  id="field-start-date"
                  type="date"
                  required
                  value={form.start_date}
                  onChange={(event) => setField('start_date', event.target.value)}
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="field-due-date" className="text-sm font-medium">
                  Due date
                </label>
                <input
                  id="field-due-date"
                  type="date"
                  required
                  value={form.due_date}
                  onChange={(event) => setField('due_date', event.target.value)}
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="field-sales-order-id" className="text-sm font-medium">
                  Linked sales order line ID
                </label>
                <input
                  id="field-sales-order-id"
                  type="text"
                  value={form.sales_order_id ?? ''}
                  onChange={(event) => setField('sales_order_id', event.target.value || undefined)}
                  placeholder="Optional: link back to a sales order line"
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                />
              </div>

              <div className="space-y-2 md:col-span-2">
                <label className="text-sm font-medium">Priority</label>
                <div className="grid gap-2 sm:grid-cols-4">
                  {PRIORITIES.map((priority) => (
                    <button
                      type="button"
                      key={priority}
                      onClick={() => setField('priority', priority)}
                      className={`rounded-lg border px-3 py-2 text-sm transition-colors ${
                        form.priority === priority
                          ? 'border-primary bg-primary text-primary-foreground'
                          : 'border-border bg-background hover:bg-muted'
                      }`}
                    >
                      {priority}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2 md:col-span-2">
                <label htmlFor="field-notes" className="text-sm font-medium">
                  Notes
                </label>
                <textarea
                  id="field-notes"
                  rows={4}
                  value={form.notes ?? ''}
                  onChange={(event) => setField('notes', event.target.value)}
                  placeholder="Shift notes, tooling remarks, or special handling"
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                />
              </div>
            </div>
          </section>
        </div>

        <div className="space-y-6">
          <section className="rounded-2xl border bg-card p-6 shadow-sm">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold">Raw Material Check</h2>
                <p className="text-sm text-muted-foreground">
                  Compare BOM requirements against live available inventory before production release.
                </p>
              </div>
              <div className="rounded-full bg-muted px-3 py-1 text-xs text-muted-foreground">
                Shortage preview
              </div>
            </div>

            {!form.product_id || !form.bom_id ? (
              <div className="rounded-xl border border-dashed bg-muted/20 px-4 py-8 text-center text-sm text-muted-foreground">
                <PackageSearch className="mx-auto mb-3 h-8 w-8 opacity-50" />
                Select a finished good and BOM to view its raw-material requirement.
              </div>
            ) : availabilityLoading ? (
              <div className="rounded-xl border bg-muted/20 px-4 py-8 text-center text-sm text-muted-foreground">
                <Loader2 className="mx-auto mb-3 h-8 w-8 animate-spin" />
                Checking inventory against BOM requirements...
              </div>
            ) : availabilityError ? (
              <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {availabilityError}
              </div>
            ) : availability ? (
              <div className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-xl border bg-muted/30 p-4">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">Raw materials</p>
                    <p className="mt-2 text-2xl font-semibold">{availability.lines.length}</p>
                  </div>
                  <div className="rounded-xl border bg-muted/30 p-4">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">Shortage lines</p>
                    <p className="mt-2 text-2xl font-semibold text-rose-600">
                      {availability.shortage_count}
                    </p>
                  </div>
                  <div className="rounded-xl border bg-muted/30 p-4">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">Status</p>
                    <p className="mt-2 text-lg font-semibold">
                      {availability.has_shortage ? 'Procurement needed' : 'Ready for production'}
                    </p>
                  </div>
                </div>

                {availability.message && (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                    {availability.message}
                  </div>
                )}

                {availability.has_shortage && (
                  <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                    <div className="flex items-start gap-3">
                      <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0" />
                      <div>
                        <p className="font-medium">Material shortage detected</p>
                        <p className="mt-1 text-amber-800">
                          You can draft a purchase order from the shortage list or proceed and let
                          procurement catch up before release.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                <div className="overflow-hidden rounded-xl border">
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[560px] text-sm">
                      <thead className="bg-muted/40 text-left">
                        <tr>
                          <th className="px-4 py-3 font-medium">Material</th>
                          <th className="px-4 py-3 font-medium text-right">Required</th>
                          <th className="px-4 py-3 font-medium text-right">Available</th>
                          <th className="px-4 py-3 font-medium text-right">Shortage</th>
                          <th className="px-4 py-3 font-medium text-right">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {availability.lines.map((line) => (
                          <tr key={line.material_id} className="border-t">
                            <td className="px-4 py-3">
                              <div className="font-medium">{line.material_name}</div>
                              <div className="text-xs text-muted-foreground">{line.material_code}</div>
                            </td>
                            <td className="px-4 py-3 text-right">
                              {formatQuantity(line.required_quantity, line.unit_code)}
                            </td>
                            <td className="px-4 py-3 text-right">
                              {formatQuantity(line.available_quantity, line.unit_code)}
                            </td>
                            <td className="px-4 py-3 text-right">
                              {formatQuantity(line.shortage_quantity, line.unit_code)}
                            </td>
                            <td className="px-4 py-3 text-right">
                              <span
                                className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium capitalize ${STATUS_STYLES[line.status]}`}
                              >
                                {line.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            ) : null}
          </section>

          <section className="rounded-2xl border bg-card p-6 shadow-sm">
            <h2 className="text-lg font-semibold">Next Step</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Create the work order now, or move to procurement if the shortage preview shows gaps.
            </p>

            <div className="mt-5 flex flex-col gap-3 sm:flex-row">
              <Button type="button" variant="outline" className="flex-1" onClick={() => navigate('/work-orders')}>
                Cancel
              </Button>
              <Button id="btn-submit-work-order" type="submit" className="flex-1" disabled={submitting}>
                {submitting ? 'Creating...' : 'Create Work Order'}
              </Button>
            </div>
          </section>
        </div>
      </form>

      <Dialog open={shortageDialogOpen} onOpenChange={setShortageDialogOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Material Shortage</DialogTitle>
            <DialogDescription>
              The selected BOM needs more raw material than current available stock. You can draft a
              purchase order now or continue with the work order.
            </DialogDescription>
          </DialogHeader>

          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            {selectedVariant?.code || 'Selected finished good'} needs {shortageLines.length} procurement action
            {shortageLines.length === 1 ? '' : 's'} before production is fully covered.
          </div>

          <div className="overflow-hidden rounded-xl border">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] text-sm">
                <thead className="bg-muted/40 text-left">
                  <tr>
                    <th className="px-4 py-3 font-medium">Material</th>
                    <th className="px-4 py-3 font-medium text-right">Required</th>
                    <th className="px-4 py-3 font-medium text-right">Available</th>
                    <th className="px-4 py-3 font-medium text-right">Shortage</th>
                  </tr>
                </thead>
                <tbody>
                  {shortageLines.map((line) => (
                    <tr key={line.material_id} className="border-t">
                      <td className="px-4 py-3">
                        <div className="font-medium">{line.material_name}</div>
                        <div className="text-xs text-muted-foreground">{line.material_code}</div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        {formatQuantity(line.required_quantity, line.unit_code)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {formatQuantity(line.available_quantity, line.unit_code)}
                      </td>
                      <td className="px-4 py-3 text-right text-rose-700">
                        {formatQuantity(line.shortage_quantity, line.unit_code)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <DialogFooter className="gap-2 sm:justify-between">
            <Button
              type="button"
              variant="outline"
              onClick={() => setShortageDialogOpen(false)}
            >
              Cancel
            </Button>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setShortageDialogOpen(false);
                  navigate('/procurement/purchase-orders', {
                    state: {
                      shortagePrefill: {
                        lines: shortageLines.map((line) => ({
                          material_id: line.material_id,
                          quantity: line.shortage_quantity,
                        })),
                        notes: `Shortage cover for ${selectedVariant?.code || form.product_id} work order.`,
                        expectedDelivery: form.start_date,
                      },
                    },
                  });
                }}
              >
                <ShoppingCart className="mr-2 h-4 w-4" />
                Create Purchase Order
              </Button>
              <Button
                type="button"
                onClick={async () => {
                  setShortageDialogOpen(false);
                  await createWorkOrder();
                }}
                disabled={submitting}
              >
                Proceed Anyway
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
