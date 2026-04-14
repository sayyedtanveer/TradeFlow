import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Download, ExternalLink, ReceiptText } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { toast } from "@/hooks/use-toast"
import { clientInvoiceStatusClasses, clientService } from "../services/client.service"
import { formatCurrency, formatDate, formatStatusLabel } from "../utils/formatters"

const invoiceStatuses = ["ALL", "DRAFT", "SENT", "PARTIAL", "PAID", "OVERDUE", "VOID"]
const pageSize = 10

export default function InvoicesList() {
  const [statusFilter, setStatusFilter] = useState("ALL")
  const [page, setPage] = useState(1)
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null)
  const [downloadingInvoiceId, setDownloadingInvoiceId] = useState<string | null>(null)

  const invoicesQuery = useQuery({
    queryKey: ["client-invoices", page, statusFilter],
    queryFn: () =>
      clientService.listInvoices({
        page,
        page_size: pageSize,
        status: statusFilter === "ALL" ? undefined : statusFilter,
      }),
  })

  const invoiceDetailQuery = useQuery({
    queryKey: ["client-invoice", selectedInvoiceId],
    queryFn: () => clientService.getInvoice(selectedInvoiceId!),
    enabled: Boolean(selectedInvoiceId),
  })

  const handleDownload = async (invoiceId: string, invoiceNumber: string) => {
    try {
      setDownloadingInvoiceId(invoiceId)
      const objectUrl = await clientService.downloadInvoicePdf(invoiceId)
      const anchor = document.createElement("a")
      anchor.href = objectUrl
      anchor.download = `${invoiceNumber}.pdf`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
      toast({
        title: "Invoice download started",
        description: `${invoiceNumber}.pdf is being prepared for download.`,
      })
    } catch (error) {
      toast({
        title: "Invoice download failed",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      })
    } finally {
      setDownloadingInvoiceId(null)
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[32px] border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Invoices</p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-900">Download invoices, review balances, and pay quickly.</h1>
            <p className="mt-3 max-w-2xl text-sm text-slate-600">
              Every invoice stays scoped to your client account, with PDF downloads and payment links from a single list.
            </p>
          </div>
          <Select
            value={statusFilter}
            onValueChange={(value) => {
              setStatusFilter(value)
              setPage(1)
            }}
          >
            <SelectTrigger className="w-[220px]">
              <SelectValue placeholder="All invoice statuses" />
            </SelectTrigger>
            <SelectContent>
              {invoiceStatuses.map((status) => (
                <SelectItem key={status} value={status}>
                  {formatStatusLabel(status)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </section>

      <Card className="rounded-[28px] border-slate-200/70">
        <CardHeader>
          <CardTitle>Invoice History</CardTitle>
          <CardDescription>Paid, unpaid, and overdue invoices stay separated by status for faster review.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {invoicesQuery.isLoading && (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <Skeleton key={index} className="h-16 rounded-2xl" />
              ))}
            </div>
          )}

          {invoicesQuery.isError && (
            <Alert variant="destructive">
              <AlertTitle>Unable to load invoices</AlertTitle>
              <AlertDescription>Refresh the portal or sign in again to reload invoice history.</AlertDescription>
            </Alert>
          )}

          {!invoicesQuery.isLoading && !invoicesQuery.isError && (
            <>
              <div className="overflow-hidden rounded-3xl border border-slate-200">
                <Table>
                  <TableHeader className="bg-slate-50">
                    <TableRow>
                      <TableHead>Invoice</TableHead>
                      <TableHead>Issued</TableHead>
                      <TableHead>Due</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                      <TableHead className="text-right">Balance</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {invoicesQuery.data?.items?.length ? (
                      invoicesQuery.data.items.map((invoice) => (
                        <TableRow key={invoice.id}>
                          <TableCell>
                            <div>
                              <p className="font-medium">{invoice.invoice_number}</p>
                              <p className="text-xs text-muted-foreground">{invoice.client_name}</p>
                            </div>
                          </TableCell>
                          <TableCell>{formatDate(invoice.invoice_date)}</TableCell>
                          <TableCell>{formatDate(invoice.due_date)}</TableCell>
                          <TableCell>
                            <Badge className={clientInvoiceStatusClasses[invoice.status] ?? "bg-slate-100 text-slate-700"}>
                              {formatStatusLabel(invoice.status)}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right font-medium">{formatCurrency(invoice.grand_total)}</TableCell>
                          <TableCell className="text-right">{formatCurrency(invoice.balance_due)}</TableCell>
                          <TableCell>
                            <div className="flex justify-end gap-2">
                              <Button variant="outline" className="rounded-full" onClick={() => setSelectedInvoiceId(invoice.id)}>
                                Details
                              </Button>
                              <Button
                                variant="outline"
                                className="rounded-full"
                                disabled={downloadingInvoiceId === invoice.id}
                                onClick={() => void handleDownload(invoice.id, invoice.invoice_number)}
                              >
                                <Download className="h-4 w-4" />
                                {downloadingInvoiceId === invoice.id ? "Preparing..." : "PDF"}
                              </Button>
                              <Button asChild className="rounded-full">
                                <a href={invoice.payment_link} target="_blank" rel="noreferrer">
                                  <ExternalLink className="h-4 w-4" />
                                  Pay
                                </a>
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={7} className="py-10 text-center text-sm text-muted-foreground">
                          No invoices match the selected filter.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>

              <div className="flex flex-col gap-3 rounded-3xl border border-slate-200 bg-slate-50 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-slate-600">
                  Page {invoicesQuery.data?.page ?? page} of {Math.max(invoicesQuery.data?.pages ?? 1, 1)}
                </p>
                <div className="flex gap-2">
                  <Button variant="outline" className="rounded-full" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    className="rounded-full"
                    disabled={!invoicesQuery.data || page >= Math.max(invoicesQuery.data.pages, 1)}
                    onClick={() => setPage((current) => current + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Dialog open={Boolean(selectedInvoiceId)} onOpenChange={(open) => !open && setSelectedInvoiceId(null)}>
        <DialogContent className="sm:max-w-5xl">
          <DialogHeader>
            <DialogTitle>Invoice Detail</DialogTitle>
            <DialogDescription>Full invoice line items, totals, and payment history.</DialogDescription>
          </DialogHeader>

          {invoiceDetailQuery.isLoading && (
            <div className="space-y-3">
              <Skeleton className="h-24 rounded-2xl" />
              <Skeleton className="h-60 rounded-2xl" />
            </div>
          )}

          {invoiceDetailQuery.isError && (
            <Alert variant="destructive">
              <AlertTitle>Unable to load invoice detail</AlertTitle>
              <AlertDescription>This invoice could not be opened right now.</AlertDescription>
            </Alert>
          )}

          {invoiceDetailQuery.data && (
            <div className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                {[
                  { label: "Invoice", value: invoiceDetailQuery.data.invoice_number },
                  { label: "Issued", value: formatDate(invoiceDetailQuery.data.invoice_date) },
                  { label: "Due", value: formatDate(invoiceDetailQuery.data.due_date) },
                  { label: "Balance Due", value: formatCurrency(invoiceDetailQuery.data.balance_due) },
                ].map((item) => (
                  <div key={item.label} className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{item.label}</p>
                    <p className="mt-2 font-semibold">{item.value}</p>
                  </div>
                ))}
              </div>

              <div className="overflow-hidden rounded-3xl border border-slate-200">
                <Table>
                  <TableHeader className="bg-slate-50">
                    <TableRow>
                      <TableHead>Description</TableHead>
                      <TableHead>Qty</TableHead>
                      <TableHead>Unit Price</TableHead>
                      <TableHead>Tax</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {invoiceDetailQuery.data.lines.length ? (
                      invoiceDetailQuery.data.lines.map((line) => (
                        <TableRow key={line.id}>
                          <TableCell>{line.description || formatStatusLabel(line.product_type)}</TableCell>
                          <TableCell>{line.quantity}</TableCell>
                          <TableCell>{formatCurrency(line.unit_price)}</TableCell>
                          <TableCell>{formatCurrency(line.tax_amount)}</TableCell>
                          <TableCell className="text-right font-medium">{formatCurrency(line.total)}</TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={5} className="py-8 text-center text-sm text-muted-foreground">
                          This invoice has no line details yet.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>

              <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
                <Card className="rounded-[28px] border-slate-200/70">
                  <CardHeader>
                    <CardTitle>Invoice Totals</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Subtotal</span>
                      <span>{formatCurrency(invoiceDetailQuery.data.subtotal)}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Discount</span>
                      <span>{formatCurrency(invoiceDetailQuery.data.discount_amount)}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Tax</span>
                      <span>{formatCurrency(invoiceDetailQuery.data.tax_amount)}</span>
                    </div>
                    <div className="flex items-center justify-between text-base font-semibold">
                      <span>Grand Total</span>
                      <span>{formatCurrency(invoiceDetailQuery.data.grand_total)}</span>
                    </div>
                  </CardContent>
                </Card>

                <Card className="rounded-[28px] border-slate-200/70">
                  <CardHeader>
                    <CardTitle>Payments</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {invoiceDetailQuery.data.payments.length ? (
                      invoiceDetailQuery.data.payments.map((payment) => (
                        <div key={payment.id} className="rounded-3xl border border-slate-200 p-4 text-sm">
                          <div className="flex items-center justify-between gap-4">
                            <div>
                              <p className="font-medium">{payment.payment_number}</p>
                              <p className="text-muted-foreground">{formatDate(payment.payment_date)}</p>
                            </div>
                            <div className="text-right">
                              <p className="font-medium">{formatCurrency(payment.amount)}</p>
                              <p className="text-muted-foreground">{formatStatusLabel(payment.payment_method)}</p>
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="rounded-3xl border border-dashed border-slate-300 p-6 text-sm text-muted-foreground">
                        No payments have been recorded against this invoice yet.
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              <div className="flex flex-wrap gap-3">
                <Button className="rounded-full" onClick={() => void handleDownload(invoiceDetailQuery.data.id, invoiceDetailQuery.data.invoice_number)}>
                  <ReceiptText className="h-4 w-4" />
                  Download PDF
                </Button>
                <Button asChild variant="outline" className="rounded-full">
                  <a href={invoiceDetailQuery.data.payment_link} target="_blank" rel="noreferrer">
                    <ExternalLink className="h-4 w-4" />
                    Open Payment Link
                  </a>
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
