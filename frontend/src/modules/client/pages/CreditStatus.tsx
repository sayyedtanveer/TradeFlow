import { useQuery } from "@tanstack/react-query"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import CreditProgress from "../components/CreditProgress"
import { clientService } from "../services/client.service"
import { clampPercent, formatCurrency } from "../utils/formatters"

export default function CreditStatus() {
  const creditQuery = useQuery({
    queryKey: ["client-credit-status"],
    queryFn: () => clientService.getCredit(),
  })

  const credit = creditQuery.data
  const remainingPercent =
    credit?.credit_limit !== null && credit?.credit_limit !== undefined && credit.credit_limit > 0
      ? clampPercent(((credit.credit_limit - credit.credit_used) / credit.credit_limit) * 100)
      : 100

  return (
    <div className="space-y-6">
      <section className="rounded-[32px] border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Credit Status</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">Monitor limit, usage, and reorder risk before you submit.</h1>
        <p className="mt-3 max-w-2xl text-sm text-slate-600">
          Credit usage is recalculated for every client account, helping you spot when the next order may need approval.
        </p>
      </section>

      {creditQuery.isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-40 rounded-[28px]" />
          <Skeleton className="h-64 rounded-[28px]" />
        </div>
      )}

      {creditQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Unable to load credit status</AlertTitle>
          <AlertDescription>Your credit summary could not be refreshed right now.</AlertDescription>
        </Alert>
      )}

      {credit && (
        <>
          {credit.is_over_limit && (
            <Alert variant="destructive">
              <AlertTitle>Credit limit exceeded</AlertTitle>
              <AlertDescription>New draft orders can still be prepared, but confirmation will likely need manual review.</AlertDescription>
            </Alert>
          )}

          {!credit.is_over_limit && credit.is_low_credit && (
            <Alert>
              <AlertTitle>Low available credit</AlertTitle>
              <AlertDescription>Your remaining credit is nearing the limit threshold used for portal alerts.</AlertDescription>
            </Alert>
          )}

          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {[
              { label: "Credit Limit", value: credit.credit_limit === null ? "Unlimited" : formatCurrency(credit.credit_limit) },
              { label: "Credit Used", value: formatCurrency(credit.credit_used) },
              { label: "Credit Remaining", value: credit.credit_remaining === null ? "Unlimited" : formatCurrency(credit.credit_remaining) },
              { label: "Usage", value: credit.usage_percent === null ? "N/A" : `${credit.usage_percent.toFixed(1)}%` },
            ].map((item) => (
              <Card key={item.label} className="rounded-[28px] border-slate-200/70">
                <CardContent className="pt-6">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{item.label}</p>
                  <p className="mt-3 text-2xl font-semibold">{item.value}</p>
                </CardContent>
              </Card>
            ))}
          </section>

          <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
            <Card className="rounded-[28px] border-slate-200/70">
              <CardHeader>
                <CardTitle>Credit Progress</CardTitle>
                <CardDescription>Portal warnings trigger as available credit drops or becomes negative.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <CreditProgress
                  limit={credit.credit_limit}
                  used={credit.credit_used}
                  remaining={credit.credit_remaining}
                  usagePercent={credit.usage_percent}
                />

                <div className="grid gap-4 sm:grid-cols-3">
                  {[
                    { label: "Limit", percent: 100, value: credit.credit_limit === null ? "Unlimited" : formatCurrency(credit.credit_limit) },
                    { label: "Used", percent: clampPercent(credit.usage_percent), value: formatCurrency(credit.credit_used) },
                    { label: "Remaining", percent: remainingPercent, value: credit.credit_remaining === null ? "Unlimited" : formatCurrency(credit.credit_remaining) },
                  ].map((item) => (
                    <div key={item.label} className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{item.label}</p>
                      <div className="mt-4 flex h-36 items-end justify-center rounded-2xl bg-white p-3">
                        <div className="w-16 rounded-t-2xl bg-slate-900 transition-all" style={{ height: `${Math.max(item.percent, 8)}%` }} />
                      </div>
                      <p className="mt-4 text-center text-sm font-medium">{item.value}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-[28px] border-slate-200/70">
              <CardHeader>
                <CardTitle>What This Means</CardTitle>
                <CardDescription>Quick guidance for interpreting client credit alerts.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-sm text-slate-600">
                <div className="rounded-3xl border border-slate-200 p-4">
                  <p className="font-medium text-slate-900">Healthy credit</p>
                  <p className="mt-2">You have room to submit reorders without immediate approval risk.</p>
                </div>
                <div className="rounded-3xl border border-slate-200 p-4">
                  <p className="font-medium text-slate-900">Low credit</p>
                  <p className="mt-2">The portal warns you before the next order pushes too close to the ceiling.</p>
                </div>
                <div className="rounded-3xl border border-slate-200 p-4">
                  <p className="font-medium text-slate-900">Over limit</p>
                  <p className="mt-2">Draft orders can still be prepared, but final confirmation may pause for finance review.</p>
                </div>
              </CardContent>
            </Card>
          </section>
        </>
      )}
    </div>
  )
}
