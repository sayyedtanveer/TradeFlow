import { RouterProvider } from "react-router-dom"
import { router } from "@/app/routes"
import { QueryProvider } from "@/app/providers/QueryProvider"
import { ErrorBoundary } from "@/components/layout/ErrorBoundary"
import { Toaster } from "@/components/ui/toaster"

export default function App() {
  return (
    <ErrorBoundary>
      <QueryProvider>
        <RouterProvider router={router} />
        <Toaster />
      </QueryProvider>
    </ErrorBoundary>
  )
}
