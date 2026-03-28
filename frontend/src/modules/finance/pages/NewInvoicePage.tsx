import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useMutation } from "@tanstack/react-query"
import { financeService } from "@/services/finance.service"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { toast } from "@/hooks/use-toast"
import { ArrowLeft, FileText, CheckCircle2 } from "lucide-react"

export default function NewInvoicePage() {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    sales_order_id: "",
    notes: "",
    terms: "Net 30",
  })

  const createMutation = useMutation({
    mutationFn: financeService.createInvoiceFromSO,
    onSuccess: (data) => {
      toast({
        title: "Invoice Created",
        description: `Successfully created invoice ${data.invoice_number}`,
      })
      navigate("/finance/invoices")
    },
    onError: (err: any) => {
      toast({
        title: "Creation Failed",
        description: err.response?.data?.detail || err.message,
        variant: "destructive",
      })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.sales_order_id) {
      toast({
        title: "Validation Error",
        description: "Sales Order ID is required",
        variant: "destructive",
      })
      return
    }
    createMutation.mutate(formData)
  }

  return (
    <div className="p-8 max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/finance/invoices")}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <FileText className="w-6 h-6 text-indigo-500" />
            Generate Sales Invoice
          </h1>
          <p className="text-slate-500 text-sm">Create an invoice from an existing Sales Order</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Invoice Details</CardTitle>
          <CardDescription>Enter the sales order reference to automatically pull line items.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Sales Order ID / Number</label>
              <Input
                placeholder="e.g. SO-2024-001 (UUID expected by backend)"
                value={formData.sales_order_id}
                onChange={(e) => setFormData({ ...formData, sales_order_id: e.target.value })}
                required
              />
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium">Payment Terms</label>
              <Input
                placeholder="e.g. Net 30"
                value={formData.terms}
                onChange={(e) => setFormData({ ...formData, terms: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Notes / Remarks</label>
              <Textarea
                rows={3}
                placeholder="Optional notes for the client"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              />
            </div>

            <div className="pt-4 flex justify-end gap-3">
              <Button type="button" variant="outline" onClick={() => navigate("/finance/invoices")}>
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending} className="bg-indigo-600 hover:bg-indigo-700">
                {createMutation.isPending ? "Generating..." : (
                  <>
                    <CheckCircle2 className="w-4 h-4 mr-2" />
                    Generate Invoice
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
