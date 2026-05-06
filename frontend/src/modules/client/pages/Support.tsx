import { useState } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import { toast } from "@/hooks/use-toast"
import { clientService } from "../services/client.service"

export default function Support() {
  const [form, setForm] = useState({ subject: "", message: "" })

  const faqQuery = useQuery({
    queryKey: ["client-support-faq"],
    queryFn: () => clientService.getFaq(),
  })

  const supportMutation = useMutation({
    mutationFn: () => clientService.submitSupportRequest(form),
    onSuccess: () => {
      toast({
        title: "Support request submitted",
        description: "The MedTrack team has been notified from inside the ERP.",
      })
      setForm({ subject: "", message: "" })
    },
    onError: (error: Error) =>
      toast({
        title: "Unable to submit support request",
        description: error.message,
        variant: "destructive",
      }),
  })

  return (
    <div className="space-y-6">
      <section className="rounded-[32px] border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Support</p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900 sm:text-3xl">Reach the MedTrack team without leaving the portal.</h1>
        <p className="mt-3 max-w-2xl text-sm text-slate-600">
          Use the contact form for order, invoice, or delivery issues, and check the FAQ for quick self-service answers.
        </p>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card className="rounded-[28px] border-slate-200/70">
          <CardHeader>
            <CardTitle>Contact Support</CardTitle>
            <CardDescription>Requests are pushed into the ERP notification flow for internal follow-up.</CardDescription>
          </CardHeader>
          <CardContent>
            <form
              className="space-y-4"
              onSubmit={(event) => {
                event.preventDefault()
                supportMutation.mutate()
              }}
            >
              <div className="space-y-2">
                <Label>Subject</Label>
                <Input value={form.subject} onChange={(event) => setForm({ ...form, subject: event.target.value })} placeholder="Invoice balance clarification" required />
              </div>
              <div className="space-y-2">
                <Label>Message</Label>
                <Textarea
                  value={form.message}
                  onChange={(event) => setForm({ ...form, message: event.target.value })}
                  placeholder="Describe the order, invoice, shipment, or credit issue you need help with."
                  className="min-h-[180px]"
                  required
                />
              </div>
              <Button type="submit" className="w-full rounded-full sm:w-auto" disabled={supportMutation.isPending}>
                {supportMutation.isPending ? "Sending..." : "Submit Support Request"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="rounded-[28px] border-slate-200/70">
            <CardHeader>
              <CardTitle>FAQ</CardTitle>
              <CardDescription>Common client portal questions answered in-app.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {faqQuery.isLoading && (
                <div className="space-y-3">
                  {Array.from({ length: 3 }).map((_, index) => (
                    <Skeleton key={index} className="h-24 rounded-2xl" />
                  ))}
                </div>
              )}

              {faqQuery.data?.map((item) => (
                <div key={item.question} className="rounded-[28px] border border-slate-200 p-5">
                  <h3 className="text-lg font-semibold text-slate-900">{item.question}</h3>
                  <p className="mt-3 text-sm leading-6 text-slate-600">{item.answer}</p>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="rounded-[28px] border-slate-200/70">
            <CardHeader>
              <CardTitle>Support Flow</CardTitle>
              <CardDescription>What happens after you submit a ticket from the client portal.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[
                { title: "1. Request sent", text: "Your message becomes an in-app alert for internal MedTrack roles." },
                { title: "2. Team review", text: "Sales, finance, or operations can review the exact client issue inside ERP." },
                { title: "3. Follow-up", text: "You keep monitoring the outcome through your orders, invoices, and notifications." },
              ].map((step) => (
                <div key={step.title} className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
                  <p className="font-medium text-slate-900">{step.title}</p>
                  <p className="mt-2 text-sm text-slate-600">{step.text}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  )
}
