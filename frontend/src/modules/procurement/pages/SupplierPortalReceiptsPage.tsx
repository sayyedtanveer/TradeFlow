import { useEffect, useState } from "react"
import { REALTIME_EVENT_NAME } from "@/components/notifications/RealtimeNotificationsBridge"
import ResponsiveDataList from "@/components/shared/ResponsiveDataList"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { useToast } from "@/hooks/use-toast"
import {
  SupplierPortalEmptyState,
  SupplierPortalHeader,
  SupplierPortalStatusBadge,
  SupplierPortalTabs,
} from "@/modules/procurement/components/SupplierPortalChrome"
import { supplyChainApi, type SupplierReceipt } from "@/services/supply-chain.service"

export default function SupplierPortalReceiptsPage() {
  const { toast } = useToast()
  const [rows, setRows] = useState<SupplierReceipt[]>([])
  const [error, setError] = useState<string | null>(null)

  const loadReceipts = async (silent = false) => {
    try {
      const response = await supplyChainApi.supplierListReceipts({ page_size: 100 })
      setRows(response.data.items)
      setError(null)
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || "Could not load receipts"
      setError(message)
      if (!silent) toast({ title: "Receipts unavailable", description: message, variant: "destructive" })
    }
  }

  useEffect(() => {
    void loadReceipts()
  }, [])

  useEffect(() => {
    const handleRealtime = () => void loadReceipts(true)
    window.addEventListener(REALTIME_EVENT_NAME, handleRealtime)
    return () => window.removeEventListener(REALTIME_EVENT_NAME, handleRealtime)
  }, [])

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-8">
      <SupplierPortalHeader
        eyebrow="Supplier workspace"
        title="Shipment notices and receipts"
        description="Track supplier ASNs and buyer-side receipt updates so dispatch and receiving stay aligned."
        backHref="/supplier-portal"
        backLabel="Portal"
      />

      <div className="erp-portal-section space-y-4">
        <SupplierPortalTabs counts={{ receipts: rows.length }} />
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </div>

      <section className="erp-portal-section space-y-4">
        <div className="space-y-1">
          <h2 className="text-xl font-semibold text-slate-950">Receipt timeline</h2>
          <p className="text-sm text-slate-600">Follow every shipment notice and receiving document that the warehouse processes for your orders.</p>
        </div>
        <ResponsiveDataList
          data={rows}
          getRowKey={(receipt) => receipt.id}
          emptyState={
            <SupplierPortalEmptyState
              title="No shipment notices or receipts yet"
              description="Open a purchase order and submit a shipment notice once goods are ready to dispatch."
              actionHref="/supplier-portal"
              actionLabel="Open portal"
            />
          }
          columns={[
            {
              key: "document",
              header: "Document",
              cell: (receipt) => (
                <div>
                  <div className="font-mono text-sm font-semibold text-slate-900">{receipt.grn_number}</div>
                  <div className="text-xs text-slate-500">{receipt.created_at ?? "-"}</div>
                </div>
              ),
            },
            {
              key: "status",
              header: "Status",
              cell: (receipt) => <SupplierPortalStatusBadge status={receipt.status} />,
            },
            {
              key: "tracking",
              header: "Tracking",
              cell: (receipt) => receipt.tracking_number ?? "-",
            },
            {
              key: "vehicle",
              header: "Vehicle",
              cell: (receipt) => receipt.vehicle_number ?? "-",
            },
            {
              key: "lines",
              header: "Lines",
              headerClassName: "text-right",
              className: "text-right",
              cell: (receipt) => receipt.lines.length,
            },
          ]}
          renderMobileCard={(receipt) => (
            <article className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <p className="font-mono text-sm font-semibold text-slate-900">{receipt.grn_number}</p>
                  <p className="text-sm text-slate-500">{receipt.created_at ?? "-"}</p>
                </div>
                <SupplierPortalStatusBadge status={receipt.status} />
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-slate-500">Tracking</p>
                  <p className="font-semibold text-slate-900">{receipt.tracking_number ?? "-"}</p>
                </div>
                <div>
                  <p className="text-slate-500">Vehicle</p>
                  <p className="font-semibold text-slate-900">{receipt.vehicle_number ?? "-"}</p>
                </div>
                <div className="col-span-2">
                  <p className="text-slate-500">Lines</p>
                  <p className="font-semibold text-slate-900">{receipt.lines.length}</p>
                </div>
              </div>
            </article>
          )}
        />
      </section>
    </div>
  )
}
