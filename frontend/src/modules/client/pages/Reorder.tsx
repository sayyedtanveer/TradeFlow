import { useEffect, useMemo, useState } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { toast } from "@/hooks/use-toast"
import { type ClientAvailability, clientService } from "../services/client.service"
import { formatCurrency, formatDate } from "../utils/formatters"

interface DraftLine {
  source_line_id: string
  product_id: string
  product_type: string
  product_name: string
  product_code?: string | null
  uom_id: string
  quantity: string
  unit_price: number
  tax_rate: number
  availability: ClientAvailability
}

export default function Reorder() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialOrderId = searchParams.get("orderId")
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(initialOrderId)
  const [draftLines, setDraftLines] = useState<DraftLine[]>([])
  const [notes, setNotes] = useState("")

  const recentOrdersQuery = useQuery({
    queryKey: ["client-orders-reorder"],
    queryFn: () => clientService.listOrders({ page: 1, page_size: 25 }),
  })

  const sourceOrderQuery = useQuery({
    queryKey: ["client-reorder-source-order", selectedOrderId],
    queryFn: () => clientService.getOrder(selectedOrderId!),
    enabled: Boolean(selectedOrderId),
  })

  const creditQuery = useQuery({
    queryKey: ["client-credit"],
    queryFn: () => clientService.getCredit(),
  })

  useEffect(() => {
    setSelectedOrderId(initialOrderId)
  }, [initialOrderId])

  useEffect(() => {
    if (!sourceOrderQuery.data) {
      return
    }

    setDraftLines(
      sourceOrderQuery.data.lines.map((line) => ({
        source_line_id: line.id,
        product_id: line.product_id,
        product_type: line.product_type,
        product_name: line.product_name,
        product_code: line.product_code,
        uom_id: line.uom_id,
        quantity: String(line.quantity),
        unit_price: line.unit_price,
        tax_rate: line.tax_rate,
        availability: line.availability,
      }))
    )
    setNotes(`Reorder from ${sourceOrderQuery.data.order_number}`)
  }, [sourceOrderQuery.data])

  const preparedLines = useMemo(
    () =>
      draftLines
        .map((line) => {
          const quantity = Number(line.quantity)
          return {
            ...line,
            quantityNumber: Number.isFinite(quantity) ? quantity : 0,
          }
        })
        .filter((line) => line.quantityNumber > 0),
    [draftLines]
  )

  const subtotal = preparedLines.reduce((sum, line) => sum + line.quantityNumber * line.unit_price, 0)
  const taxTotal = preparedLines.reduce((sum, line) => sum + line.quantityNumber * line.unit_price * (line.tax_rate / 100), 0)
  const estimatedTotal = subtotal + taxTotal
  const projectedUsage = (creditQuery.data?.credit_used ?? 0) + estimatedTotal
  const overLimit =
    creditQuery.data?.credit_limit !== null && creditQuery.data?.credit_limit !== undefined
      ? projectedUsage > creditQuery.data.credit_limit
      : false
  const lineWarnings = preparedLines.filter(
    (line) => line.availability.available_quantity !== null && line.quantityNumber > line.availability.available_quantity
  )
  const unknownAvailability = preparedLines.filter((line) => line.availability.available_quantity === null)

  const reorderMutation = useMutation({
    mutationFn: () =>
      clientService.reorder({
        order_id: selectedOrderId!,
        notes,
        lines: preparedLines.map((line) => ({
          product_id: line.product_id,
          product_type: line.product_type,
          uom_id: line.uom_id,
          quantity: line.quantityNumber,
          unit_price: line.unit_price,
          tax_rate: line.tax_rate,
        })),
      }),
    onSuccess: (order) => {
      toast({
        title: "Draft reorder created",
        description: `Order ${order.order_number} has been created in draft status.`,
      })
      navigate(`/client/orders/${order.id}`)
    },
    onError: (error: Error) =>
      toast({
        title: "Unable to create reorder",
        description: error.message,
        variant: "destructive",
      }),
  })

  const selectOrder = (orderId: string) => {
    setSelectedOrderId(orderId)
    setSearchParams({ orderId })
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[32px] border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Reorder</p>
            <h1 className="mt-2 text-2xl font-semibold text-slate-900 sm:text-3xl">Start a draft order from your order history.</h1>
            <p className="mt-3 max-w-2xl text-sm text-slate-600">
              Pick a previous order, adjust quantities, review stock and credit warnings, then submit a fresh draft for the team to confirm.
            </p>
          </div>
          <div className="erp-kpi-gradient-soft w-full rounded-3xl px-5 py-4 text-white sm:max-w-xs">
            <p className="text-xs uppercase tracking-[0.2em] text-white/75">Estimated Draft Total</p>
            <p className="mt-2 text-2xl font-semibold">{formatCurrency(estimatedTotal, formatCurrency(0))}</p>
            <p className="text-sm text-white/75">subtotal plus estimated tax</p>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="rounded-[28px] border-slate-200/70">
          <CardHeader>
            <CardTitle>Select Previous Order</CardTitle>
            <CardDescription>Choose from recent order history to prefill the reorder draft.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Source Order</Label>
              <Select value={selectedOrderId ?? undefined} onValueChange={selectOrder}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose an order" />
                </SelectTrigger>
                <SelectContent>
                  {recentOrdersQuery.data?.items.map((order) => (
                    <SelectItem key={order.id} value={order.id}>
                      {order.order_number} - {formatDate(order.order_date)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {recentOrdersQuery.isLoading && (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, index) => (
                  <Skeleton key={index} className="h-16 rounded-2xl" />
                ))}
              </div>
            )}

            <div className="space-y-3">
              {recentOrdersQuery.data?.items.map((order) => (
                <button
                  key={order.id}
                  type="button"
                  className={`w-full rounded-3xl border p-4 text-left transition ${
                    selectedOrderId === order.id ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200 bg-slate-50 hover:border-slate-400"
                  }`}
                  onClick={() => selectOrder(order.id)}
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="font-medium">{order.order_number}</p>
                      <p className={`text-sm ${selectedOrderId === order.id ? "text-slate-300" : "text-slate-500"}`}>
                        Delivery {formatDate(order.delivery_date)}
                      </p>
                    </div>
                    <p className="text-sm font-medium">{formatCurrency(order.grand_total)}</p>
                  </div>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          {sourceOrderQuery.isLoading && (
            <div className="space-y-4">
              <Skeleton className="h-24 rounded-[28px]" />
              <Skeleton className="h-80 rounded-[28px]" />
            </div>
          )}

          {!selectedOrderId && (
            <Alert>
              <AlertTitle>Select a source order</AlertTitle>
              <AlertDescription>Choose an order from the left to start building a draft reorder.</AlertDescription>
            </Alert>
          )}

          {sourceOrderQuery.data && (
            <>
              <Card className="rounded-[28px] border-slate-200/70">
                <CardHeader>
                  <CardTitle>Draft Summary</CardTitle>
                  <CardDescription>
                    Based on {sourceOrderQuery.data.order_number}, originally scheduled for delivery on {formatDate(sourceOrderQuery.data.delivery_date)}.
                  </CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4 md:grid-cols-3">
                  <div className="rounded-3xl bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Original Total</p>
                    <p className="mt-2 text-lg font-semibold">{formatCurrency(sourceOrderQuery.data.grand_total)}</p>
                  </div>
                  <div className="rounded-3xl bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Projected Credit Used</p>
                    <p className="mt-2 text-lg font-semibold">{formatCurrency(projectedUsage)}</p>
                  </div>
                  <div className="rounded-3xl bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Remaining Credit</p>
                    <p className="mt-2 text-lg font-semibold">
                      {creditQuery.data?.credit_limit === null || creditQuery.data?.credit_limit === undefined
                        ? "Unlimited"
                        : formatCurrency(creditQuery.data.credit_limit - projectedUsage)}
                    </p>
                  </div>
                </CardContent>
              </Card>

              {overLimit && (
                <Alert variant="destructive">
                  <AlertTitle>Credit limit warning</AlertTitle>
                  <AlertDescription>
                    This reorder draft exceeds the available credit and may require manual approval before confirmation.
                  </AlertDescription>
                </Alert>
              )}

              {lineWarnings.length > 0 && (
                <Alert>
                  <AlertTitle>Backorder risk detected</AlertTitle>
                  <AlertDescription>
                    {lineWarnings.length} line item{lineWarnings.length > 1 ? "s" : ""} exceed currently available stock.
                  </AlertDescription>
                </Alert>
              )}

              {unknownAvailability.length > 0 && (
                <Alert>
                  <AlertTitle>Availability pending</AlertTitle>
                  <AlertDescription>
                    {unknownAvailability.length} line item{unknownAvailability.length > 1 ? "s" : ""} will be confirmed during planning because live stock data is not available.
                  </AlertDescription>
                </Alert>
              )}

              <Card className="rounded-[28px] border-slate-200/70">
                <CardHeader>
                  <CardTitle>Edit Quantities</CardTitle>
                  <CardDescription>Set any line to zero if you do not want it included in the new draft.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-4 md:hidden">
                    {draftLines.map((line) => {
                      const quantity = Number(line.quantity) || 0
                      const estimatedLineTotal = quantity * line.unit_price * (1 + line.tax_rate / 100)
                      const exceedsAvailability =
                        line.availability.available_quantity !== null && quantity > line.availability.available_quantity

                      return (
                        <div key={line.source_line_id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="text-base font-semibold text-slate-900">{line.product_name}</p>
                              <p className="mt-1 text-xs text-slate-500">{line.product_code || line.product_type}</p>
                            </div>
                            <span className={`text-sm font-medium ${exceedsAvailability ? "text-rose-600" : "text-slate-700"}`}>
                              {formatCurrency(estimatedLineTotal)}
                            </span>
                          </div>
                          <div className="mt-4 space-y-2">
                            <Label htmlFor={`qty-${line.source_line_id}`}>Quantity</Label>
                            <Input
                              id={`qty-${line.source_line_id}`}
                              type="number"
                              min="0"
                              step="0.01"
                              value={line.quantity}
                              onChange={(event) =>
                                setDraftLines((current) =>
                                  current.map((item) =>
                                    item.source_line_id === line.source_line_id ? { ...item, quantity: event.target.value } : item
                                  )
                                )
                              }
                            />
                          </div>
                          <div className="mt-4 space-y-2 text-sm">
                            <div className="flex items-center justify-between gap-3">
                              <span className="text-slate-500">Unit price</span>
                              <span>{formatCurrency(line.unit_price)}</span>
                            </div>
                            <div className="flex items-start justify-between gap-3">
                              <span className="text-slate-500">Availability</span>
                              <span className={`max-w-[55%] text-right ${exceedsAvailability ? "text-rose-600" : "text-slate-700"}`}>
                                {line.availability.message}
                              </span>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>

                  <div className="hidden overflow-hidden rounded-3xl border border-slate-200 md:block">
                    <Table>
                      <TableHeader className="bg-slate-50">
                        <TableRow>
                          <TableHead>Product</TableHead>
                          <TableHead>Quantity</TableHead>
                          <TableHead>Availability</TableHead>
                          <TableHead className="text-right">Unit Price</TableHead>
                          <TableHead className="text-right">Est. Line Total</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {draftLines.map((line) => {
                          const quantity = Number(line.quantity) || 0
                          const estimatedLineTotal = quantity * line.unit_price * (1 + line.tax_rate / 100)
                          const exceedsAvailability =
                            line.availability.available_quantity !== null && quantity > line.availability.available_quantity

                          return (
                            <TableRow key={line.source_line_id}>
                              <TableCell>
                                <div>
                                  <p className="font-medium">{line.product_name}</p>
                                  <p className="text-xs text-muted-foreground">{line.product_code || line.product_type}</p>
                                </div>
                              </TableCell>
                              <TableCell className="w-[180px]">
                                <Input
                                  type="number"
                                  min="0"
                                  step="0.01"
                                  value={line.quantity}
                                  onChange={(event) =>
                                    setDraftLines((current) =>
                                      current.map((item) =>
                                        item.source_line_id === line.source_line_id ? { ...item, quantity: event.target.value } : item
                                      )
                                    )
                                  }
                                />
                              </TableCell>
                              <TableCell>
                                <p className={`text-sm ${exceedsAvailability ? "text-rose-600" : "text-slate-700"}`}>{line.availability.message}</p>
                              </TableCell>
                              <TableCell className="text-right">{formatCurrency(line.unit_price)}</TableCell>
                              <TableCell className="text-right font-medium">{formatCurrency(estimatedLineTotal)}</TableCell>
                            </TableRow>
                          )
                        })}
                      </TableBody>
                    </Table>
                  </div>

                  <div className="space-y-2">
                    <Label>Draft Notes</Label>
                    <Textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Any delivery or quantity changes for this reorder" />
                  </div>

                  <div className="flex flex-col gap-4 rounded-3xl bg-slate-50 p-5 md:flex-row md:items-center md:justify-between">
                    <div className="space-y-1 text-sm">
                      <p className="font-medium text-slate-900">Draft totals</p>
                      <p className="text-slate-600">
                        Subtotal {formatCurrency(subtotal)} + tax {formatCurrency(taxTotal)}
                      </p>
                    </div>
                    <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
                      <Button asChild variant="outline" className="w-full rounded-full sm:w-auto">
                        <Link to="/client/orders">Back to Orders</Link>
                      </Button>
                      <Button
                        className="w-full rounded-full sm:w-auto"
                        disabled={!selectedOrderId || preparedLines.length === 0 || reorderMutation.isPending}
                        onClick={() => reorderMutation.mutate()}
                      >
                        {reorderMutation.isPending ? "Submitting..." : "Create Draft Reorder"}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </section>
    </div>
  )
}
