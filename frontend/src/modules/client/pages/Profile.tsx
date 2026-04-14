import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useAuthStore } from "@/app/store/authStore"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { toast } from "@/hooks/use-toast"
import { type ClientAddress, type ClientNotificationSettings, clientService } from "../services/client.service"
import { formatAddress, formatCurrency } from "../utils/formatters"

interface AddressFormState {
  type: "billing" | "shipping"
  label: string
  contact_name: string
  address_line1: string
  address_line2: string
  city: string
  state: string
  postal_code: string
  country: string
  phone: string
  email: string
  is_default: boolean
}

const emptyAddressForm: AddressFormState = {
  type: "shipping",
  label: "",
  contact_name: "",
  address_line1: "",
  address_line2: "",
  city: "",
  state: "",
  postal_code: "",
  country: "",
  phone: "",
  email: "",
  is_default: false,
}

const emptyNotificationSettings: ClientNotificationSettings = {
  order_confirmed: false,
  order_shipped: false,
  order_delivered: false,
  invoice_overdue: false,
  low_credit: false,
  marketing: false,
}

export default function Profile() {
  const queryClient = useQueryClient()
  const { user, setUser } = useAuthStore()
  const [contactForm, setContactForm] = useState({ first_name: "", last_name: "", email: "" })
  const [notificationForm, setNotificationForm] = useState<ClientNotificationSettings>(emptyNotificationSettings)
  const [addressForm, setAddressForm] = useState<AddressFormState>(emptyAddressForm)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingAddress, setEditingAddress] = useState<ClientAddress | null>(null)

  const profileQuery = useQuery({
    queryKey: ["client-profile"],
    queryFn: () => clientService.getProfile(),
  })

  useEffect(() => {
    if (!profileQuery.data) {
      return
    }

    setContactForm({
      first_name: profileQuery.data.contact.first_name,
      last_name: profileQuery.data.contact.last_name,
      email: profileQuery.data.contact.email,
    })
    setNotificationForm(profileQuery.data.notifications)
  }, [profileQuery.data])

  const contactMutation = useMutation({
    mutationFn: () => clientService.updateProfile(contactForm),
    onSuccess: (data) => {
      toast({
        title: "Contact updated",
        description: "Your primary client portal contact details have been saved.",
      })
      void queryClient.invalidateQueries({ queryKey: ["client-profile"] })
      if (user) {
        setUser({
          ...user,
          first_name: data.first_name,
          last_name: data.last_name,
          email: data.email,
        })
      }
    },
    onError: (error: Error) =>
      toast({
        title: "Unable to update contact",
        description: error.message,
        variant: "destructive",
      }),
  })

  const notificationMutation = useMutation({
    mutationFn: () => clientService.updateNotificationSettings(notificationForm),
    onSuccess: (settings) => {
      setNotificationForm(settings)
      toast({
        title: "Notification preferences saved",
        description: "Client notification settings have been updated.",
      })
      void queryClient.invalidateQueries({ queryKey: ["client-profile"] })
      void queryClient.invalidateQueries({ queryKey: ["client-notifications"] })
    },
    onError: (error: Error) =>
      toast({
        title: "Unable to save notification settings",
        description: error.message,
        variant: "destructive",
      }),
  })

  const addressMutation = useMutation({
    mutationFn: () =>
      editingAddress
        ? clientService.updateAddress(editingAddress.id, addressForm)
        : clientService.createAddress(addressForm),
    onSuccess: () => {
      toast({
        title: editingAddress ? "Address updated" : "Address added",
        description: "Client address book changes have been saved.",
      })
      setIsDialogOpen(false)
      setEditingAddress(null)
      setAddressForm(emptyAddressForm)
      void queryClient.invalidateQueries({ queryKey: ["client-profile"] })
    },
    onError: (error: Error) =>
      toast({
        title: "Unable to save address",
        description: error.message,
        variant: "destructive",
      }),
  })

  const deleteAddressMutation = useMutation({
    mutationFn: (addressId: string) => clientService.deleteAddress(addressId),
    onSuccess: () => {
      toast({
        title: "Address deleted",
        description: "The selected address has been removed from this client account.",
      })
      void queryClient.invalidateQueries({ queryKey: ["client-profile"] })
    },
    onError: (error: Error) =>
      toast({
        title: "Unable to delete address",
        description: error.message,
        variant: "destructive",
      }),
  })

  const openCreateAddress = () => {
    setEditingAddress(null)
    setAddressForm(emptyAddressForm)
    setIsDialogOpen(true)
  }

  const openEditAddress = (address: ClientAddress) => {
    setEditingAddress(address)
    setAddressForm({
      type: address.type,
      label: address.label ?? "",
      contact_name: address.contact_name ?? "",
      address_line1: address.address_line1,
      address_line2: address.address_line2 ?? "",
      city: address.city ?? "",
      state: address.state ?? "",
      postal_code: address.postal_code ?? "",
      country: address.country ?? "",
      phone: address.phone ?? "",
      email: address.email ?? "",
      is_default: address.is_default,
    })
    setIsDialogOpen(true)
  }

  if (profileQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-24 rounded-[28px]" />
        <Skeleton className="h-96 rounded-[28px]" />
      </div>
    )
  }

  if (!profileQuery.data) {
    return (
      <Card className="rounded-[28px] border-slate-200/70">
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          Unable to load your client profile at the moment.
        </CardContent>
      </Card>
    )
  }

  const profile = profileQuery.data

  return (
    <div className="space-y-6">
      <section className="rounded-[32px] border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Profile</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">Manage contact details, addresses, and alerts.</h1>
        <p className="mt-3 max-w-2xl text-sm text-slate-600">
          Company information stays view-only, while client contact, address book, and notification preferences remain editable here.
        </p>
      </section>

      <Tabs defaultValue="company" className="space-y-6">
        <TabsList className="h-auto flex-wrap rounded-3xl bg-slate-100 p-2">
          <TabsTrigger value="company" className="rounded-2xl px-5 py-2">Company Info</TabsTrigger>
          <TabsTrigger value="contact" className="rounded-2xl px-5 py-2">Contacts</TabsTrigger>
          <TabsTrigger value="addresses" className="rounded-2xl px-5 py-2">Addresses</TabsTrigger>
          <TabsTrigger value="notifications" className="rounded-2xl px-5 py-2">Notifications</TabsTrigger>
        </TabsList>

        <TabsContent value="company">
          <Card className="rounded-[28px] border-slate-200/70">
            <CardHeader>
              <CardTitle>Company Information</CardTitle>
              <CardDescription>This section is view-only and reflects master data maintained in the ERP.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {[
                { label: "Client Code", value: profile.company.code },
                { label: "Company Name", value: profile.company.name },
                { label: "Email", value: profile.company.email || "--" },
                { label: "Phone", value: profile.company.phone || "--" },
                { label: "GST Number", value: profile.company.gst_number || "--" },
                { label: "Payment Terms", value: `${profile.company.payment_terms_days} days` },
                { label: "Credit Limit", value: profile.company.credit_limit === null ? "Unlimited" : formatCurrency(profile.company.credit_limit) },
                { label: "Credit Used", value: formatCurrency(profile.company.credit_used) },
                { label: "Registered Address", value: profile.company.address || "--" },
              ].map((field) => (
                <div key={field.label} className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{field.label}</p>
                  <p className="mt-2 font-medium">{field.value}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="contact">
          <Card className="rounded-[28px] border-slate-200/70">
            <CardHeader>
              <CardTitle>Primary Contact</CardTitle>
              <CardDescription>Update the person responsible for portal activity, invoice follow-up, and order notifications.</CardDescription>
            </CardHeader>
            <CardContent>
              <form
                className="grid gap-4 md:grid-cols-2"
                onSubmit={(event) => {
                  event.preventDefault()
                  contactMutation.mutate()
                }}
              >
                <div className="space-y-2">
                  <Label>First Name</Label>
                  <Input value={contactForm.first_name} onChange={(event) => setContactForm({ ...contactForm, first_name: event.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label>Last Name</Label>
                  <Input value={contactForm.last_name} onChange={(event) => setContactForm({ ...contactForm, last_name: event.target.value })} />
                </div>
                <div className="space-y-2 md:col-span-2">
                  <Label>Email</Label>
                  <Input type="email" value={contactForm.email} onChange={(event) => setContactForm({ ...contactForm, email: event.target.value })} />
                </div>
                <div className="md:col-span-2">
                  <Button type="submit" className="rounded-full" disabled={contactMutation.isPending}>
                    {contactMutation.isPending ? "Saving..." : "Save Contact"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="addresses">
          <Card className="rounded-[28px] border-slate-200/70">
            <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle>Address Book</CardTitle>
                <CardDescription>Maintain multiple shipping and billing destinations for the client account.</CardDescription>
              </div>
              <Button className="rounded-full" onClick={openCreateAddress}>Add Address</Button>
            </CardHeader>
            <CardContent className="grid gap-4 lg:grid-cols-2">
              {profile.addresses.length ? (
                profile.addresses.map((address) => (
                  <div key={address.id} className="rounded-[28px] border border-slate-200 p-5">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge className={address.type === "billing" ? "bg-blue-100 text-blue-700" : "bg-emerald-100 text-emerald-700"}>
                        {address.type}
                      </Badge>
                      {address.is_default && <Badge variant="outline">Default</Badge>}
                    </div>
                    <h3 className="mt-4 text-lg font-semibold">{address.label || "Unlabeled Address"}</h3>
                    <p className="mt-2 text-sm text-slate-600">{formatAddress(address)}</p>
                    {address.contact_name && <p className="mt-3 text-sm text-slate-600">Contact: {address.contact_name}</p>}
                    {address.phone && <p className="text-sm text-slate-600">Phone: {address.phone}</p>}
                    {address.email && <p className="text-sm text-slate-600">Email: {address.email}</p>}
                    <div className="mt-5 flex gap-2">
                      <Button variant="outline" className="rounded-full" onClick={() => openEditAddress(address)}>
                        Edit
                      </Button>
                      <Button
                        variant="destructive"
                        className="rounded-full"
                        disabled={deleteAddressMutation.isPending}
                        onClick={() => deleteAddressMutation.mutate(address.id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-[28px] border border-dashed border-slate-300 p-6 text-sm text-muted-foreground">
                  No client addresses have been added yet.
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications">
          <Card className="rounded-[28px] border-slate-200/70">
            <CardHeader>
              <CardTitle>Notification Preferences</CardTitle>
              <CardDescription>Choose which in-app alerts should appear in the client portal.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {[
                { key: "order_confirmed", label: "Order confirmed", description: "Alert me when an order moves out of draft." },
                { key: "order_shipped", label: "Order shipped", description: "Show notifications when a shipment leaves the warehouse." },
                { key: "order_delivered", label: "Order delivered", description: "Confirm when delivery is marked complete." },
                { key: "invoice_overdue", label: "Invoice overdue", description: "Highlight invoices that have passed due date." },
                { key: "low_credit", label: "Low credit", description: "Warn me when available credit becomes tight." },
                { key: "marketing", label: "Product updates", description: "Receive optional announcements from MedTrack." },
              ].map((item) => (
                <label key={item.key} className="flex items-start gap-3 rounded-3xl border border-slate-200 p-4">
                  <Checkbox
                    checked={notificationForm[item.key as keyof ClientNotificationSettings]}
                    onCheckedChange={(checked) =>
                      setNotificationForm((current) => ({
                        ...current,
                        [item.key]: checked === true,
                      }))
                    }
                  />
                  <div>
                    <p className="font-medium text-slate-900">{item.label}</p>
                    <p className="mt-1 text-sm text-slate-600">{item.description}</p>
                  </div>
                </label>
              ))}
              <Button className="rounded-full" disabled={notificationMutation.isPending} onClick={() => notificationMutation.mutate()}>
                {notificationMutation.isPending ? "Saving..." : "Save Preferences"}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>{editingAddress ? "Edit Address" : "Add Address"}</DialogTitle>
            <DialogDescription>Billing and shipping destinations are always scoped to this client account only.</DialogDescription>
          </DialogHeader>

          <form
            className="grid gap-4 md:grid-cols-2"
            onSubmit={(event) => {
              event.preventDefault()
              addressMutation.mutate()
            }}
          >
            <div className="space-y-2">
              <Label>Type</Label>
              <Select value={addressForm.type} onValueChange={(value) => setAddressForm({ ...addressForm, type: value as AddressFormState["type"] })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="billing">Billing</SelectItem>
                  <SelectItem value="shipping">Shipping</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Label</Label>
              <Input value={addressForm.label} onChange={(event) => setAddressForm({ ...addressForm, label: event.target.value })} placeholder="Head Office" />
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label>Contact Name</Label>
              <Input value={addressForm.contact_name} onChange={(event) => setAddressForm({ ...addressForm, contact_name: event.target.value })} />
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label>Address Line 1</Label>
              <Input value={addressForm.address_line1} onChange={(event) => setAddressForm({ ...addressForm, address_line1: event.target.value })} required />
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label>Address Line 2</Label>
              <Input value={addressForm.address_line2} onChange={(event) => setAddressForm({ ...addressForm, address_line2: event.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>City</Label>
              <Input value={addressForm.city} onChange={(event) => setAddressForm({ ...addressForm, city: event.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>State</Label>
              <Input value={addressForm.state} onChange={(event) => setAddressForm({ ...addressForm, state: event.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>Postal Code</Label>
              <Input value={addressForm.postal_code} onChange={(event) => setAddressForm({ ...addressForm, postal_code: event.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>Country</Label>
              <Input value={addressForm.country} onChange={(event) => setAddressForm({ ...addressForm, country: event.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>Phone</Label>
              <Input value={addressForm.phone} onChange={(event) => setAddressForm({ ...addressForm, phone: event.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input type="email" value={addressForm.email} onChange={(event) => setAddressForm({ ...addressForm, email: event.target.value })} />
            </div>
            <label className="md:col-span-2 flex items-center gap-3 rounded-3xl border border-slate-200 p-4">
              <Checkbox checked={addressForm.is_default} onCheckedChange={(checked) => setAddressForm({ ...addressForm, is_default: checked === true })} />
              <div>
                <p className="font-medium text-slate-900">Make default {addressForm.type} address</p>
                <p className="text-sm text-slate-600">Only one default address is kept for each address type.</p>
              </div>
            </label>
            <div className="md:col-span-2">
              <Button type="submit" className="rounded-full" disabled={addressMutation.isPending}>
                {addressMutation.isPending ? "Saving..." : editingAddress ? "Save Address" : "Add Address"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
