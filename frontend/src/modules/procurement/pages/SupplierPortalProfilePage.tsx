import { useEffect, useState } from "react"
import { REALTIME_EVENT_NAME } from "@/components/notifications/RealtimeNotificationsBridge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/hooks/use-toast"
import {
  SupplierPortalHeader,
  SupplierPortalTabs,
} from "@/modules/procurement/components/SupplierPortalChrome"
import {
  supplyChainApi,
  type SupplierProfile,
  type SupplierProfileUpdateInput,
} from "@/services/supply-chain.service"

const emptyForm: SupplierProfileUpdateInput = {
  contact_person: "",
  email: "",
  phone: "",
  address: "",
  gst: "",
  payment_terms: "",
}

export default function SupplierPortalProfilePage() {
  const { toast } = useToast()
  const [profile, setProfile] = useState<SupplierProfile | null>(null)
  const [form, setForm] = useState<SupplierProfileUpdateInput>(emptyForm)
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const loadProfile = async (silent = false) => {
    try {
      const response = await supplyChainApi.supplierProfile()
      setProfile(response.data)
      setForm({
        contact_person: response.data.contact_person ?? "",
        email: response.data.email ?? "",
        phone: response.data.phone ?? "",
        address: response.data.address ?? "",
        gst: response.data.gst ?? "",
        payment_terms: response.data.payment_terms ?? "",
      })
      setError(null)
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || "Could not load supplier profile"
      setError(message)
      if (!silent) toast({ title: "Profile unavailable", description: message, variant: "destructive" })
    }
  }

  useEffect(() => {
    void loadProfile()
  }, [])

  useEffect(() => {
    const handleRealtime = () => void loadProfile(true)
    window.addEventListener(REALTIME_EVENT_NAME, handleRealtime)
    return () => window.removeEventListener(REALTIME_EVENT_NAME, handleRealtime)
  }, [])

  const updateField = (key: keyof SupplierProfileUpdateInput, value: string) => {
    setForm((current) => ({ ...current, [key]: value }))
  }

  const saveProfile = async () => {
    setIsSaving(true)
    try {
      const response = await supplyChainApi.supplierUpdateProfile(form)
      setProfile(response.data)
      toast({ title: "Profile updated" })
    } catch (err: any) {
      toast({
        title: "Profile update failed",
        description: err?.response?.data?.detail || err?.message,
        variant: "destructive",
      })
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-8">
      <SupplierPortalHeader
        eyebrow="Supplier workspace"
        title="Supplier profile"
        description="Keep contact, payment, and statutory details current so the buyer always sees the latest supplier master record."
        backHref="/supplier-portal"
        backLabel="Portal"
        actions={
          <Button onClick={saveProfile} disabled={isSaving} className="w-full sm:w-auto">
            {isSaving ? "Saving..." : "Save profile"}
          </Button>
        }
      />

      <div className="erp-portal-section space-y-4">
        <SupplierPortalTabs />
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </div>

      {profile && (
        <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.72fr)]">
          <article className="erp-portal-section space-y-4">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="space-y-1">
                <p className="text-sm text-slate-500">Supplier</p>
                <p className="text-2xl font-semibold text-slate-950">{profile.name}</p>
                <p className="font-mono text-xs text-slate-500">{profile.code}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                Keep the buyer-facing supplier master accurate and complete.
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Contact person</Label>
                <Input value={form.contact_person ?? ""} onChange={(event) => updateField("contact_person", event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Email</Label>
                <Input value={form.email ?? ""} onChange={(event) => updateField("email", event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Phone</Label>
                <Input value={form.phone ?? ""} onChange={(event) => updateField("phone", event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>GST / Tax ID</Label>
                <Input value={form.gst ?? ""} onChange={(event) => updateField("gst", event.target.value)} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Address</Label>
              <Textarea value={form.address ?? ""} onChange={(event) => updateField("address", event.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Payment terms</Label>
              <Input value={form.payment_terms ?? ""} onChange={(event) => updateField("payment_terms", event.target.value)} />
            </div>
          </article>

          <article className="erp-portal-section space-y-4">
            <div className="space-y-1">
              <h2 className="text-xl font-semibold text-slate-950">Profile readiness</h2>
              <p className="text-sm text-slate-600">A more complete profile helps buyers process orders, invoices, and payments faster.</p>
            </div>
            <div className="rounded-[24px] border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium text-slate-700">Profile completeness</p>
                <span className="text-sm font-semibold text-slate-900">{profile.profile_completeness ?? 0}%</span>
              </div>
              <Progress value={profile.profile_completeness ?? 0} className="mt-3" />
            </div>
            <div className="rounded-[24px] border border-dashed border-slate-300 bg-slate-50 p-4 text-sm leading-6 text-slate-600">
              Review email, phone, GST, and payment terms regularly. The buyer uses this information when sharing orders and settling invoices.
            </div>
          </article>
        </section>
      )}
    </div>
  )
}
