import { RouterProvider } from "react-router-dom"
import { router } from "@/app/routes"
import { QueryProvider } from "@/app/providers/QueryProvider"
import { ErrorBoundary } from "@/components/layout/ErrorBoundary"
import { useAuthInitialize } from "@/hooks/useAuthInitialize"

function AppContent() {
  // Validate token on app initialization
  useAuthInitialize()

  return <RouterProvider router={router} />
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
