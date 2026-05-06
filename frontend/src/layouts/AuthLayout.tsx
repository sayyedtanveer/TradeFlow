import { Outlet, Navigate } from "react-router-dom"
import { useAuthStore } from "@/app/store/authStore"

export default function AuthLayout() {
  const { isAuthenticated } = useAuthStore()

  if (isAuthenticated) {
    // If already logged in, redirect to dashboard
    return <Navigate to="/" replace />
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#f8fafc] p-4">
      <div className="w-full max-w-sm sm:max-w-md">
        <div className="mb-8 text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-600">MedTrack ERP</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">Sign in to your account</h1>
          <p className="mt-2 text-sm text-slate-500">Secure access to your production, procurement, and finance workspace</p>
        </div>
        <Outlet />
      </div>
    </div>
  )
}
