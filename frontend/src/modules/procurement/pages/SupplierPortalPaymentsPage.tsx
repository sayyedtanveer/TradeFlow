import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { REALTIME_EVENT_NAME } from "@/components/notifications/RealtimeNotificationsBridge"
import { supplyChainApi, type SupplierPayment } from "@/services/supply-chain.service"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useToast } from "@/hooks/use-toast"

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
    <div className="max-w-5xl space-y-6">
      <Button variant="ghost" size="sm" asChild>
        <Link to="/supplier-portal">{"<- Portal"}</Link>
      </Button>
      <div>
        <h1 className="text-2xl font-semibold">Supplier payments</h1>
        <p className="text-sm text-muted-foreground">View buyer payments against submitted supplier invoices.</p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {!error && rows.length === 0 ? (
        <Alert>
          <AlertDescription>No payments recorded yet.</AlertDescription>
        </Alert>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Payment</TableHead>
              <TableHead>Date</TableHead>
              <TableHead>Method</TableHead>
              <TableHead>Reference</TableHead>
              <TableHead className="text-right">Amount</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((payment) => (
              <TableRow key={payment.id}>
                <TableCell className="font-mono">{payment.payment_number}</TableCell>
                <TableCell>{payment.payment_date ?? "-"}</TableCell>
                <TableCell>{payment.payment_method ?? "-"}</TableCell>
                <TableCell>{payment.reference_number ?? "-"}</TableCell>
                <TableCell className="text-right">{formatCurrency(payment.amount)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
