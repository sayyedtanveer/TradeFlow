import { useMemo, useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { useNavigate, useSearchParams } from "react-router-dom"
import { useAuthStore } from "@/app/store/authStore"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { clientService } from "../services/client.service"

type Mode = "login" | "forgot" | "reset"

export default function ClientLogin() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const { setAuth, setUser, setSupplierAndClient } = useAuthStore()
  const [loginForm, setLoginForm] = useState({ email: "", password: "", tenant_id: "" })
  const [forgotForm, setForgotForm] = useState({ email: "", tenant_id: "" })
  const [resetForm, setResetForm] = useState({ token: searchParams.get("token") ?? "", new_password: "" })
  const [message, setMessage] = useState<string | null>(null)

  const mode = useMemo<Mode>(() => {
    const raw = searchParams.get("mode")
    return raw === "forgot" || raw === "reset" ? raw : "login"
  }, [searchParams])

  const loginMutation = useMutation({
    mutationFn: clientService.login,
    onSuccess: async (session) => {
      setAuth(session.access_token, session.tenant_id)
      setSupplierAndClient(null, session.client_id)
      try {
        const profile = await clientService.getProfile()
        setUser({
          id: profile.contact.id,
          email: profile.contact.email,
          first_name: profile.contact.first_name,
          last_name: profile.contact.last_name,
          role: "CLIENT",
          client_id: session.client_id,
          tenant_id: session.tenant_id,
          is_active: true,
        })
      } catch {
        const names = session.full_name.split(" ")
        setUser({
          id: session.user_id,
          email: session.email,
          first_name: names[0] ?? "Client",
          last_name: names.slice(1).join(" "),
          role: "CLIENT",
          client_id: session.client_id,
          tenant_id: session.tenant_id,
          is_active: true,
        })
      }
      navigate("/client", { replace: true })
    },
    onError: (error: any) => setMessage(error.message ?? "Unable to sign in."),
  })

  const forgotMutation = useMutation({
    mutationFn: clientService.forgotPassword,
    onSuccess: (data) => {
      setMessage(data.reset_token ? `Reset token: ${data.reset_token}` : data.message)
      setResetForm((current) => ({ ...current, token: data.reset_token ?? current.token }))
      setSearchParams({ mode: "reset", token: data.reset_token ?? "" })
    },
    onError: (error: any) => setMessage(error.message ?? "Unable to start password reset."),
  })

  const resetMutation = useMutation({
    mutationFn: clientService.resetPassword,
    onSuccess: (data) => {
      setMessage(data.message)
      setSearchParams({ mode: "login" })
      setResetForm({ token: "", new_password: "" })
    },
    onError: (error: any) => setMessage(error.message ?? "Unable to reset password."),
  })

  const setMode = (nextMode: Mode) => {
    setMessage(null)
    setSearchParams(nextMode === "login" ? {} : { mode: nextMode })
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#dbeafe_0%,#fff7ed_45%,#ffffff_100%)] px-4 py-12">
      <div className="mx-auto max-w-5xl">
        <div className="grid gap-8 md:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-[32px] border border-white/60 bg-white/70 p-8 shadow-2xl backdrop-blur">
            <p className="text-xs uppercase tracking-[0.3em] text-slate-500">MedTrack Client Portal</p>
            <h1 className="mt-4 text-4xl font-semibold leading-tight text-slate-900">Track orders, download invoices, and reorder from one client workspace.</h1>
            <p className="mt-4 max-w-xl text-slate-600">
              Use your dedicated client account to follow delivery progress, monitor credit usage, manage addresses, and reach support without touching the internal ERP.
            </p>
            <div className="mt-8 grid gap-4 sm:grid-cols-3">
              {["Order timeline", "Invoice download", "Credit alerts"].map((item) => (
                <div key={item} className="rounded-3xl bg-slate-950 p-5 text-white">
                  <p className="text-sm font-medium">{item}</p>
                </div>
              ))}
            </div>
          </div>

          <Card className="rounded-[32px] border-slate-200/70 shadow-2xl">
            <CardHeader>
              <CardTitle>Client Access</CardTitle>
              <CardDescription>Sign in with your client role account. Password recovery stays inside this portal.</CardDescription>
              <div className="mt-4 flex gap-2">
                <Button variant={mode === "login" ? "default" : "outline"} className="rounded-full" onClick={() => setMode("login")}>Login</Button>
                <Button variant={mode === "forgot" ? "default" : "outline"} className="rounded-full" onClick={() => setMode("forgot")}>Forgot Password</Button>
                <Button variant={mode === "reset" ? "default" : "outline"} className="rounded-full" onClick={() => setMode("reset")}>Reset</Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {message && <div className="rounded-2xl bg-slate-100 px-4 py-3 text-sm text-slate-700">{message}</div>}

              {mode === "login" && (
                <form
                  className="space-y-4"
                  onSubmit={(event) => {
                    event.preventDefault()
                    loginMutation.mutate(loginForm)
                  }}
                >
                  <div className="space-y-2">
                    <Label>Email</Label>
                    <Input type="email" value={loginForm.email} onChange={(event) => setLoginForm({ ...loginForm, email: event.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Password</Label>
                    <Input type="password" value={loginForm.password} onChange={(event) => setLoginForm({ ...loginForm, password: event.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Tenant ID</Label>
                    <Input value={loginForm.tenant_id} onChange={(event) => setLoginForm({ ...loginForm, tenant_id: event.target.value })} placeholder="Workspace UUID" />
                  </div>
                  <Button type="submit" className="w-full rounded-full" disabled={loginMutation.isPending}>
                    {loginMutation.isPending ? "Signing In..." : "Enter Client Portal"}
                  </Button>
                </form>
              )}

              {mode === "forgot" && (
                <form
                  className="space-y-4"
                  onSubmit={(event) => {
                    event.preventDefault()
                    forgotMutation.mutate(forgotForm)
                  }}
                >
                  <div className="space-y-2">
                    <Label>Email</Label>
                    <Input type="email" value={forgotForm.email} onChange={(event) => setForgotForm({ ...forgotForm, email: event.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Tenant ID</Label>
                    <Input value={forgotForm.tenant_id} onChange={(event) => setForgotForm({ ...forgotForm, tenant_id: event.target.value })} placeholder="Workspace UUID" />
                  </div>
                  <Button type="submit" className="w-full rounded-full" disabled={forgotMutation.isPending}>
                    {forgotMutation.isPending ? "Generating..." : "Send Reset Instructions"}
                  </Button>
                </form>
              )}

              {mode === "reset" && (
                <form
                  className="space-y-4"
                  onSubmit={(event) => {
                    event.preventDefault()
                    resetMutation.mutate(resetForm)
                  }}
                >
                  <div className="space-y-2">
                    <Label>Reset Token</Label>
                    <Input value={resetForm.token} onChange={(event) => setResetForm({ ...resetForm, token: event.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>New Password</Label>
                    <Input type="password" value={resetForm.new_password} onChange={(event) => setResetForm({ ...resetForm, new_password: event.target.value })} />
                  </div>
                  <Button type="submit" className="w-full rounded-full" disabled={resetMutation.isPending}>
                    {resetMutation.isPending ? "Updating..." : "Set New Password"}
                  </Button>
                </form>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
