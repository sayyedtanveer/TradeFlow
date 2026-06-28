import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, AlertTriangle, Barcode, Boxes, Package, RotateCcw, Search } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import BarcodeScannerModal from '@/components/barcode/BarcodeScannerModal';
import storekeeperService, {
  type IssueQueueItem,
  type OperationalBatchItem,
  type PendingReturnItem,
} from '@/services/storekeeper.service';

const qty = (value: number | null | undefined) => Number(value ?? 0).toFixed(3);
const tone = (status: string) => {
  const s = status.toUpperCase();
  if (['QUARANTINED', 'DAMAGE_HOLD'].includes(s)) return 'destructive';
  if (['QC_HOLD', 'PICKING_HOLD', 'INVESTIGATION_HOLD', 'EXPIRED'].includes(s)) return 'secondary';
  return 'outline';
};

export default function StorekeeperDashboardPage() {
  const queryClient = useQueryClient();
  const [issueQty, setIssueQty] = useState<Record<string, string>>({});
  const [returnQty, setReturnQty] = useState<Record<string, string>>({});
  const [traceQuery, setTraceQuery] = useState('');
  const [scannerOpen, setScannerOpen] = useState(false);
  const [expandedBatch, setExpandedBatch] = useState<string | null>(null);

  const issueRes = useQuery({ queryKey: ['storekeeper-issue-queue'], queryFn: storekeeperService.getIssueQueue });
  const shortageRes = useQuery({ queryKey: ['storekeeper-shortage-queue'], queryFn: storekeeperService.getShortageQueue });
  const reservationRes = useQuery({ queryKey: ['storekeeper-reservations'], queryFn: storekeeperService.getPendingReservations });
  const returnsRes = useQuery({ queryKey: ['storekeeper-returns'], queryFn: storekeeperService.getPendingReturns });
  const alertsRes = useQuery({ queryKey: ['storekeeper-alerts'], queryFn: storekeeperService.getInventoryAlerts });
  const batchesRes = useQuery({ queryKey: ['storekeeper-batches'], queryFn: storekeeperService.getOperationalBatches });
  const traceRes = useQuery({
    queryKey: ['storekeeper-traceability', traceQuery],
    queryFn: () => storekeeperService.searchTraceability(traceQuery),
    enabled: traceQuery.trim().length > 0,
  });

  const refresh = () => queryClient.invalidateQueries();
  const issueMutation = useMutation({
    mutationFn: (item: IssueQueueItem) => {
      const key = `${item.work_order_id}-${item.material_id}-${item.batch_id ?? 'auto'}`;
      return storekeeperService.issueMaterial({
        work_order_id: item.work_order_id,
        material_id: item.material_id,
        quantity: Number(issueQty[key] ?? item.remaining_quantity),
        batch_id: item.batch_id ?? null,
      });
    },
    onSuccess: refresh,
  });
  const returnMutation = useMutation({
    mutationFn: (item: PendingReturnItem) => {
      const key = `${item.reservation_id}-${item.batch_id ?? 'auto'}`;
      return storekeeperService.returnMaterial({
        work_order_id: item.work_order_id,
        material_id: item.material_id,
        quantity: Number(returnQty[key] ?? item.returnable_quantity),
        batch_id: item.batch_id ?? null,
      });
    },
    onSuccess: refresh,
  });

  const issueQueue = issueRes.data?.data ?? [];
  const shortages = shortageRes.data?.data ?? [];
  const reservations = reservationRes.data?.data ?? [];
  const returns = returnsRes.data?.data ?? [];
  const alerts = alertsRes.data?.data ?? [];
  const batches = batchesRes.data?.data ?? [];
  const nearEmptyCount = batches.filter((b) => b.is_near_empty).length;
  const blockedCount = batches.filter((b) => b.is_blocked).length;
  const traceItems = traceRes.data?.data?.items ?? [];
  const traceResolved = traceRes.data?.data?.resolved;
  const summaryCards = [
    { label: 'Pending reservations', value: reservations.length, Icon: Package },
    { label: 'Shortages', value: shortages.length, Icon: AlertTriangle },
    { label: 'Pending returns', value: returns.length, Icon: RotateCcw },
    { label: 'Near-empty batches', value: nearEmptyCount, Icon: Boxes },
    { label: 'Blocked stock', value: blockedCount, Icon: AlertCircle },
    { label: 'Alerts', value: alerts.length, Icon: AlertCircle },
  ];

  const activeBatches = useMemo(
    () => batches.filter((b) => b.remaining_quantity > 0 || b.is_blocked),
    [batches],
  );

  if ([issueRes, shortageRes, reservationRes, returnsRes, alertsRes, batchesRes].some((q) => q.isLoading)) {
    return <div className="p-8">Loading Storekeeper Workspace...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="sticky top-0 z-10 flex flex-col gap-4 border-b bg-background/95 pb-4 pt-4 backdrop-blur md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-600">Warehouse execution</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">Storekeeper Workspace</h1>
          <p className="mt-2 text-muted-foreground">Pick, issue, return, and trace measured raw materials without leaving the queue.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setScannerOpen(true)}><Barcode className="mr-2 h-4 w-4" />Scan</Button>
          <Button variant="outline" onClick={refresh}>Refresh queues</Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        {summaryCards.map(({ label, value, Icon }) => (
          <Card key={label}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>{label}</span>
                <Icon className="h-4 w-4" />
              </div>
              <div className="mt-3 text-2xl font-bold">{value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Operational pick queue</CardTitle>
          <Badge variant="outline">{issueQueue.length} ready</Badge>
        </CardHeader>
        <CardContent className="space-y-3">
          {issueQueue.length === 0 && <p className="text-sm text-muted-foreground">No pending material issues.</p>}
          {issueQueue.map((item) => {
            const key = `${item.work_order_id}-${item.material_id}-${item.batch_id ?? 'auto'}`;
            return (
              <div key={key} className="rounded-2xl border p-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono font-semibold text-blue-700">{item.wo_number}</span>
                      <Badge variant="outline">{item.material_code ?? 'ITEM'}</Badge>
                      {item.batch_number && <Badge variant="secondary">Batch {item.batch_number}</Badge>}
                    </div>
                    <p className="mt-2 font-medium">{item.material_name}</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Required {qty(item.required_quantity)} · Reserved {qty(item.reserved_quantity)} · Issued {qty(item.issued_quantity)} · Remaining {qty(item.remaining_quantity)}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Input
                      type="number"
                      className="w-28"
                      min={0}
                      max={item.remaining_quantity}
                      value={issueQty[key] ?? String(item.remaining_quantity)}
                      onChange={(e) => setIssueQty((prev) => ({ ...prev, [key]: e.target.value }))}
                    />
                    <Button onClick={() => issueMutation.mutate(item)}>Issue</Button>
                  </div>
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
        <Card>
          <CardHeader><CardTitle>Batch visibility</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {activeBatches.map((batch: OperationalBatchItem) => (
              <button
                key={batch.batch_id}
                className="w-full rounded-2xl border p-4 text-left transition hover:bg-muted/40"
                onClick={() => setExpandedBatch(expandedBatch === batch.batch_id ? null : batch.batch_id)}
              >
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono font-semibold">{batch.batch_number}</span>
                      <Badge variant="outline">{batch.material_code}</Badge>
                      <Badge variant={tone(batch.status)}>{batch.status}</Badge>
                      {batch.is_near_empty && <Badge variant="secondary">Near empty</Badge>}
                    </div>
                    <p className="mt-2 font-medium">{batch.material_name}</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {batch.location_name ?? 'Unassigned location'}{batch.location_type ? ` · ${batch.location_type}` : ''}
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-x-5 gap-y-1 text-sm md:text-right">
                    <span className="text-muted-foreground">Remaining</span><span className="font-semibold text-emerald-700">{qty(batch.remaining_quantity)}</span>
                    <span className="text-muted-foreground">Reserved</span><span>{qty(batch.reserved_quantity)}</span>
                  </div>
                </div>
                {expandedBatch === batch.batch_id && (
                  <div className="mt-4 grid gap-3 border-t pt-4 text-sm md:grid-cols-4">
                    <div><span className="text-muted-foreground">Original</span><div className="font-semibold">{qty(batch.original_quantity)}</div></div>
                    <div><span className="text-muted-foreground">Consumed</span><div className="font-semibold">{qty(batch.consumed_quantity)}</div></div>
                    <div><span className="text-muted-foreground">Returned</span><div className="font-semibold">{qty(batch.returned_quantity)}</div></div>
                    <div><span className="text-muted-foreground">Expiry</span><div className="font-semibold">{batch.expiry_date ?? '—'}</div></div>
                  </div>
                )}
              </button>
            ))}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle>Return queue</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {returns.length === 0 && <p className="text-sm text-muted-foreground">No issued material awaiting return.</p>}
              {returns.map((item) => {
                const key = `${item.reservation_id}-${item.batch_id ?? 'auto'}`;
                return (
                  <div key={key} className="rounded-xl border p-3">
                    <div className="font-medium">{item.material_code} · {item.batch_number ?? 'Auto batch'}</div>
                    <div className="mt-1 text-sm text-muted-foreground">
                      {item.wo_number} · Returnable {qty(item.returnable_quantity)}
                    </div>
                    <div className="mt-3 flex gap-2">
                      <Input
                        type="number"
                        className="w-28"
                        value={returnQty[key] ?? String(item.returnable_quantity)}
                        onChange={(e) => setReturnQty((prev) => ({ ...prev, [key]: e.target.value }))}
                      />
                      <Button variant="outline" onClick={() => returnMutation.mutate(item)}>Return</Button>
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Traceability lookup</CardTitle></CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Input
                  placeholder="Item code or batch number"
                  value={traceQuery}
                  onChange={(e) => setTraceQuery(e.target.value)}
                />
                <Button variant="outline" onClick={() => setScannerOpen(true)}><Search className="h-4 w-4" /></Button>
              </div>
              {traceResolved && (
                <p className="mt-3 text-sm text-muted-foreground">
                  Resolved {traceResolved.type}: {traceResolved.code ?? traceResolved.batch_number ?? traceResolved.wo_number ?? traceQuery}
                </p>
              )}
              <div className="mt-4 space-y-2">
                {traceItems.slice(0, 6).map((item: any) => (
                  <div key={item.transaction_id} className="rounded-xl border p-3 text-sm">
                    <div className="font-medium">{item.transaction_type}</div>
                    <div className="text-muted-foreground">
                      Batch {item.batch_number ?? '—'} · Qty {qty(item.quantity)} · WO {item.wo_number ?? '—'}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <BarcodeScannerModal
        isOpen={scannerOpen}
        onClose={() => setScannerOpen(false)}
        onScan={(value) => setTraceQuery(value)}
        title="Scan material or batch"
        description="Use barcode or QR to jump directly into traceability."
      />
    </div>
  );
}
