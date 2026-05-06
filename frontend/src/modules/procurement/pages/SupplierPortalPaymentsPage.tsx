import { useEffect, useState } from "react"
import { REALTIME_EVENT_NAME } from "@/components/notifications/RealtimeNotificationsBridge"
import ResponsiveDataList from "@/components/shared/ResponsiveDataList"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { useToast } from "@/hooks/use-toast"
import {
  SupplierPortalEmptyState,
  SupplierPortalHeader,
  SupplierPortalTabs,
} from "@/modules/procurement/components/SupplierPortalChrome"
import { supplyChainApi, type SupplierPayment } from "@/services/supply-chain.service"

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(value)

export default function SupplierPortalPaymentsPage() {
  const { toast } = useToast()
  const [rows, setRows] = useState<SupplierPayment[]>([])
  const [error, setError] = useState<string | null>(null)

  const loadPayments = async (silent = false) => {
    try {
      const response = await supplyChainApi.supplierListPayments({ page_size: 100 })
      setRows(response.data.items)
      setError(null)
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || "Could not load payments"
      setError(message)
      if (!silent) toast({ title: "Payments unavailable", description: message, variant: "destructive" })
    }
  }

  useEffect(() => {
    void loadPayments()
  }, [])

  useEffect(() => {
    const handleRealtime = () => void loadPayments(true)
    window.addEventListener(REALTIME_EVENT_NAME, handleRealtime)
    return () => window.removeEventListener(REALTIME_EVENT_NAME, handleRealtime)
  }, [])

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-8">
      <SupplierPortalHeader
        eyebrow="Supplier workspace"
        title="Supplier payments"
        description="Keep a clear record of buyer payments, references, and settlement activity against submitted invoices."
        backHref="/supplier-portal"
        backLabel="Portal"
      />

      <div className="erp-portal-section space-y-4">
        <SupplierPortalTabs counts={{ payments: rows.length }} />
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </div>

      <section className="erp-portal-section space-y-4">
        <div className="space-y-1">
          <h2 className="text-xl font-semibold text-slate-950">Payment history</h2>
          <p className="text-sm text-slate-600">Review payment dates, settlement references, and remittance methods from the buyer.</p>
        </div>
        <ResponsiveDataList
          data={rows}
          getRowKey={(payment) => payment.id}
          emptyState={
            <SupplierPortalEmptyState
              title="No payments recorded yet"
              description="Payments will appear here once the buyer settles a submitted supplier invoice."
              actionHref="/supplier-portal/invoices"
              actionLabel="View invoices"
            />
          }
          columns={[
            {
              key: "payment",
              header: "Payment",
              cell: (payment) => <span className="font-mono text-sm font-semibold text-slate-900">{payment.payment_number}</span>,
            },
            {
              key: "date",
              header: "Date",
              cell: (payment) => payment.payment_date ?? "-",
            },
            {
              key: "method",
              header: "Method",
              cell: (payment) => payment.payment_method ?? "-",
            },
            {
              key: "reference",
              header: "Reference",
              cell: (payment) => payment.reference_number ?? "-",
            },
            {
              key: "amount",
              header: "Amount",
              headerClassName: "text-right",
              className: "text-right",
              cell: (payment) => <span className="font-semibold text-slate-900">{formatCurrency(payment.amount)}</span>,
            },
          ]}
          renderMobileCard={(payment) => (
            <article className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm">
              <div className="space-y-1">
                <p className="font-mono text-sm font-semibold text-slate-900">{payment.payment_number}</p>
                <p className="text-sm text-slate-500">{payment.payment_date ?? "-"}</p>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-slate-500">Method</p>
                  <p className="font-semibold text-slate-900">{payment.payment_method ?? "-"}</p>
                </div>
                <div>
                  <p className="text-slate-500">Reference</p>
                  <p className="font-semibold text-slate-900">{payment.reference_number ?? "-"}</p>
                </div>
                <div className="col-span-2">
                  <p className="text-slate-500">Amount</p>
                  <p className="font-semibold text-slate-900">{formatCurrency(payment.amount)}</p>
                </div>
              </div>
            </article>
          )}
        />
      </section>
    </div>
  )
}
