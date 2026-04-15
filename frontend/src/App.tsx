import { RouterProvider } from "react-router-dom"
import { router } from "@/app/routes"
import { QueryProvider } from "@/app/providers/QueryProvider"
import { ErrorBoundary } from "@/components/layout/ErrorBoundary"

export default function App() {
  return (
    <ErrorBoundary>
      <QueryProvider>
        <RouterProvider router={router} />
      </QueryProvider>
    </ErrorBoundary>
  )
}
