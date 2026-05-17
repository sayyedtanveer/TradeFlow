import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { AlertCircle, Package, AlertTriangle } from 'lucide-react';
import storekeeperService, {
  type IssueQueueItem,
  type ShortageQueueItem,
} from '@/services/storekeeper.service';

export default function StorekeeperDashboardPage() {
  const queryClient = useQueryClient();
  const [issueQty, setIssueQty] = useState<Record<string, string>>({});

  const { data: issueRes, isLoading: issueLoading } = useQuery({
    queryKey: ['storekeeper-issue-queue'],
    queryFn: () => storekeeperService.getIssueQueue(),
  });
  const { data: shortageRes, isLoading: shortageLoading } = useQuery({
    queryKey: ['storekeeper-shortage-queue'],
    queryFn: () => storekeeperService.getShortageQueue(),
  });
  const { data: partialRes, isLoading: partialLoading } = useQuery({
    queryKey: ['storekeeper-partially-issued'],
    queryFn: () => storekeeperService.getPartiallyIssued(),
  });

  const issueMutation = useMutation({
    mutationFn: (item: IssueQueueItem) => {
      const key = `${item.work_order_id}-${item.material_id}-${item.batch_id ?? 'auto'}`;
      const qty = Number(issueQty[key] ?? item.remaining_quantity);
      return storekeeperService.issueMaterial({
        work_order_id: item.work_order_id,
        material_id: item.material_id,
        quantity: qty,
        batch_id: item.batch_id ?? null,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['storekeeper-issue-queue'] });
      queryClient.invalidateQueries({ queryKey: ['storekeeper-partially-issued'] });
    },
  });

  const issueQueue = issueRes?.data ?? [];
  const shortageQueue = (shortageRes?.data ?? []) as ShortageQueueItem[];
  const partiallyIssued = partialRes?.data ?? [];

  if (issueLoading || shortageLoading || partialLoading) {
    return <div className="p-8">Loading Storekeeper Dashboard...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="sticky top-0 z-10 bg-background/95 backdrop-blur pb-4 border-b pt-4 flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Storekeeper Workspace</h1>
          <p className="text-muted-foreground mt-2">
            Issue materials, track shortages, and manage partial issues.
          </p>
        </div>
        <Button variant="outline" onClick={() => queryClient.invalidateQueries()}>
          Refresh queues
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border-l-4 border-l-blue-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Package className="w-4 h-4 text-blue-500" />
              Pending Issues
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-bold">{issueQueue.length}</span>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-orange-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-orange-500" />
              Shortages
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-bold">{shortageQueue.length}</span>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-amber-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-500" />
              Partially Issued WOs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-bold">{Array.isArray(partiallyIssued) ? partiallyIssued.length : 0}</span>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Material Issue Queue</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {issueQueue.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>WO</TableHead>
                  <TableHead>Material</TableHead>
                  <TableHead>Batch</TableHead>
                  <TableHead>Required</TableHead>
                  <TableHead>Reserved</TableHead>
                  <TableHead>Issued</TableHead>
                  <TableHead>Consumed</TableHead>
                  <TableHead>Returned</TableHead>
                  <TableHead>Remaining</TableHead>
                  <TableHead>Issue Qty</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {issueQueue.map((issue: IssueQueueItem) => {
                  const key = `${issue.work_order_id}-${issue.material_id}-${issue.batch_id ?? 'auto'}`;
                  const materialLabel = issue.material_code
                    ? `${issue.material_code} - ${issue.material_name ?? 'Material'}`
                    : issue.material_name ?? 'Material';
                  return (
                    <TableRow key={key}>
                      <TableCell className="font-medium">{issue.wo_number}</TableCell>
                      <TableCell className="max-w-[220px] truncate" title={materialLabel}>
                        {materialLabel}
                      </TableCell>
                      <TableCell>{issue.batch_number ?? 'Auto'}</TableCell>
                      <TableCell>{issue.required_quantity}</TableCell>
                      <TableCell>{issue.reserved_quantity ?? 0}</TableCell>
                      <TableCell>{issue.issued_quantity}</TableCell>
                      <TableCell>{issue.consumed_quantity ?? 0}</TableCell>
                      <TableCell>{issue.returned_quantity ?? 0}</TableCell>
                      <TableCell className="font-semibold">{issue.remaining_quantity}</TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          className="w-24 h-9"
                          min={0}
                          max={issue.remaining_quantity}
                          value={issueQty[key] ?? String(issue.remaining_quantity)}
                          onChange={(e) => setIssueQty((p) => ({ ...p, [key]: e.target.value }))}
                        />
                      </TableCell>
                      <TableCell>
                        <Button
                          size="sm"
                          disabled={issueMutation.isPending}
                          onClick={() => issueMutation.mutate(issue)}
                        >
                          Issue
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">No pending issues</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Shortages</CardTitle>
        </CardHeader>
        <CardContent>
          {shortageQueue.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>WO</TableHead>
                  <TableHead>Material</TableHead>
                  <TableHead>Shortage</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {shortageQueue.map((s) => {
                  const materialLabel = s.material_code
                    ? `${s.material_code} - ${s.material_name ?? 'Material'}`
                    : s.material_name ?? 'Material';
                  return (
                    <TableRow key={s.shortage_id}>
                      <TableCell className="font-medium">{s.wo_number ?? 'Unassigned WO'}</TableCell>
                      <TableCell className="max-w-[220px] truncate" title={materialLabel}>
                        {materialLabel}
                      </TableCell>
                      <TableCell className="text-red-600 font-semibold">{s.shortage_quantity}</TableCell>
                      <TableCell>
                        <Badge variant="destructive">{s.status}</Badge>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">No shortages</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
