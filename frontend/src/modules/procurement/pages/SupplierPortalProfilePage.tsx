import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { REALTIME_EVENT_NAME } from "@/components/notifications/RealtimeNotificationsBridge"
import {
  supplyChainApi,
  type SupplierProfile,
  type SupplierProfileUpdateInput,
} from "@/services/supply-chain.service"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/hooks/use-toast"

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
    <div className="max-w-3xl space-y-6">
      <Button variant="ghost" size="sm" asChild>
        <Link to="/supplier-portal">{"<- Portal"}</Link>
      </Button>

      <div>
        <h1 className="text-2xl font-semibold">Supplier profile</h1>
        <p className="text-sm text-muted-foreground">
          Maintain contact, tax, address, and payment details visible to the buyer.
        </p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {profile && (
        <section className="rounded-xl border bg-card p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-sm text-muted-foreground">Supplier</p>
              <p className="text-lg font-semibold">{profile.name}</p>
              <p className="font-mono text-xs text-muted-foreground">{profile.code}</p>
            </div>
            <div className="min-w-52">
              <p className="text-sm text-muted-foreground">Profile completeness</p>
              <Progress value={profile.profile_completeness ?? 0} className="mt-2" />
              <p className="mt-1 text-xs text-muted-foreground">{profile.profile_completeness ?? 0}% complete</p>
            </div>
          </div>
        </section>
      )}

      <section className="rounded-xl border bg-card p-4 space-y-4">
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
        <Button onClick={saveProfile} disabled={isSaving}>
          {isSaving ? "Saving..." : "Save profile"}
        </Button>
      </section>
    </div>
  )
}
