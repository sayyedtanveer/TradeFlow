import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { ScrollText } from "lucide-react"
import { REALTIME_EVENT_NAME } from "@/components/notifications/RealtimeNotificationsBridge"
import ResponsiveDataList from "@/components/shared/ResponsiveDataList"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { useToast } from "@/hooks/use-toast"
import {
  SupplierPortalEmptyState,
  SupplierPortalHeader,
  SupplierPortalStatusBadge,
  SupplierPortalTabs,
} from "@/modules/procurement/components/SupplierPortalChrome"
import { supplyChainApi, type SupplierInvoice } from "@/services/supply-chain.service"

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(value)

export default function SupplierPortalInvoicesPage() {
  const { toast } = useToast()
  const [rows, setRows] = useState<SupplierInvoice[]>([])
  const [error, setError] = useState<string | null>(null)

  const loadInvoices = async (silent = false) => {
    try {
      const response = await supplyChainApi.supplierListInvoices({ page_size: 100 })
      setRows(response.data.items)
      setError(null)
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || "Could not load invoices"
      setError(message)
      if (!silent) toast({ title: "Invoices unavailable", description: message, variant: "destructive" })
    }
  }

  useEffect(() => {
    void loadInvoices()
  }, [])

  useEffect(() => {
    const handleRealtime = () => void loadInvoices(true)
    window.addEventListener(REALTIME_EVENT_NAME, handleRealtime)
    return () => window.removeEventListener(REALTIME_EVENT_NAME, handleRealtime)
  }, [])

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-8">
      <SupplierPortalHeader
        eyebrow="Supplier workspace"
        title="Supplier invoices"
        description="Track submitted invoices, watch balances, and understand what still needs buyer payment attention."
        backHref="/supplier-portal"
        backLabel="Portal"
        actions={
          <Button asChild className="w-full sm:w-auto">
            <Link to="/supplier-portal/invoices/new">
              <ScrollText className="h-4 w-4" />
              Submit invoice
            </Link>
          </Button>
        }
      />

      <div className="erp-portal-section space-y-4">
        <SupplierPortalTabs counts={{ invoices: rows.length }} />
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </div>

      <section className="erp-portal-section space-y-4">
        <div className="space-y-1">
          <h2 className="text-xl font-semibold text-slate-950">Invoice register</h2>
          <p className="text-sm text-slate-600">Every supplier invoice stays visible here along with payment balance and due timeline.</p>
        </div>
        <ResponsiveDataList
          data={rows}
          getRowKey={(invoice) => invoice.id}
          emptyState={
            <SupplierPortalEmptyState
              title="No supplier invoices submitted yet"
              description="Submit the first invoice once a purchase order or receipt is ready for billing."
              actionHref="/supplier-portal/invoices/new"
              actionLabel="Submit invoice"
            />
          }
          columns={[
            {
              key: "invoice",
              header: "Invoice",
              cell: (invoice) => (
                <div>
                  <div className="font-mono text-sm font-semibold text-slate-900">{invoice.invoice_number}</div>
                  {invoice.supplier_invoice_ref && (
                    <div className="text-xs text-slate-500">{invoice.supplier_invoice_ref}</div>
                  )}
                </div>
              ),
            },
            {
              key: "status",
              header: "Status",
              cell: (invoice) => <SupplierPortalStatusBadge status={invoice.status} />,
            },
            {
              key: "invoiceDate",
              header: "Invoice date",
              cell: (invoice) => invoice.invoice_date ?? "-",
            },
            {
              key: "dueDate",
              header: "Due date",
              cell: (invoice) => invoice.due_date ?? "-",
            },
            {
              key: "total",
              header: "Total",
              headerClassName: "text-right",
              className: "text-right",
              cell: (invoice) => <span className="font-semibold text-slate-900">{formatCurrency(invoice.grand_total)}</span>,
            },
            {
              key: "balance",
              header: "Balance",
              headerClassName: "text-right",
              className: "text-right",
              cell: (invoice) => formatCurrency(invoice.balance_due),
            },
          ]}
          renderMobileCard={(invoice) => (
            <article className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <p className="font-mono text-sm font-semibold text-slate-900">{invoice.invoice_number}</p>
                  <p className="text-sm text-slate-500">{invoice.invoice_date ?? "-"}</p>
                </div>
                <SupplierPortalStatusBadge status={invoice.status} />
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-slate-500">Total</p>
                  <p className="font-semibold text-slate-900">{formatCurrency(invoice.grand_total)}</p>
                </div>
                <div>
                  <p className="text-slate-500">Balance</p>
                  <p className="font-semibold text-slate-900">{formatCurrency(invoice.balance_due)}</p>
                </div>
                <div>
                  <p className="text-slate-500">Due date</p>
                  <p className="font-semibold text-slate-900">{invoice.due_date ?? "-"}</p>
                </div>
                <div>
                  <p className="text-slate-500">Reference</p>
                  <p className="font-semibold text-slate-900">{invoice.supplier_invoice_ref ?? "-"}</p>
                </div>
              </div>
            </article>
          )}
        />
      </section>
    </div>
  )
}
