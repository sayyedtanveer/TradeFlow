import { RouterProvider } from "react-router-dom"
import { router } from "@/app/routes"
import { QueryProvider } from "@/app/providers/QueryProvider"
import { ErrorBoundary } from "@/components/layout/ErrorBoundary"
import { RealtimeNotificationsBridge } from "@/components/notifications/RealtimeNotificationsBridge"
import { useAuthInitialize } from "@/hooks/useAuthInitialize"

function AppContent() {
  // Validate token on app initialization
  useAuthInitialize()

  return (
    <>
      <RealtimeNotificationsBridge />
      <RouterProvider router={router} />
    </>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <QueryProvider>
        <AppContent />
      </QueryProvider>
    </ErrorBoundary>
  )
}
