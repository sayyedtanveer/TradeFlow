import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { REALTIME_EVENT_NAME } from "@/components/notifications/RealtimeNotificationsBridge"
import { supplyChainApi, type SupplierInvoice } from "@/services/supply-chain.service"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useToast } from "@/hooks/use-toast"

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
    <div className="max-w-5xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/supplier-portal">{"<- Portal"}</Link>
        </Button>
        <Button asChild>
          <Link to="/supplier-portal/invoices/new">Submit invoice</Link>
        </Button>
      </div>

      <div>
        <h1 className="text-2xl font-semibold">Supplier invoices</h1>
        <p className="text-sm text-muted-foreground">Track submitted invoices, payment status, and balances.</p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {!error && rows.length === 0 ? (
        <Alert>
          <AlertDescription>No supplier invoices submitted yet.</AlertDescription>
        </Alert>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Invoice</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Invoice date</TableHead>
              <TableHead>Due date</TableHead>
              <TableHead className="text-right">Total</TableHead>
              <TableHead className="text-right">Balance</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((invoice) => (
              <TableRow key={invoice.id}>
                <TableCell>
                  <div className="font-mono text-sm">{invoice.invoice_number}</div>
                  {invoice.supplier_invoice_ref && (
                    <div className="text-xs text-muted-foreground">{invoice.supplier_invoice_ref}</div>
                  )}
                </TableCell>
                <TableCell>
                  <Badge variant="secondary">{invoice.status}</Badge>
                </TableCell>
                <TableCell>{invoice.invoice_date ?? "-"}</TableCell>
                <TableCell>{invoice.due_date ?? "-"}</TableCell>
                <TableCell className="text-right">{formatCurrency(invoice.grand_total)}</TableCell>
                <TableCell className="text-right">{formatCurrency(invoice.balance_due)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
