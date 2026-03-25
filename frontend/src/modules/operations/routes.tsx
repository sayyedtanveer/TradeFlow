import { lazy, Suspense } from "react"
import { RouteObject } from "react-router-dom"
import { ProtectedRoute } from "@/app/routes/ProtectedRoute"

const OperationsListPage = lazy(() => import("./pages/OperationsListPage"))
const OperationFormPage = lazy(() => import("./pages/OperationFormPage"))

const PageLoading = () => <div className="p-8 flex items-center justify-center">Loading...</div>

export const operationsRoutes: RouteObject[] = [
  {
    path: "operations",
    element: <Suspense fallback={<PageLoading />}><OperationsListPage /></Suspense>,
  },
  {
    path: "operations/new",
    element: (
      <ProtectedRoute roles={["ADMIN", "MANAGER"]}>
        <Suspense fallback={<PageLoading />}><OperationFormPage /></Suspense>
      </ProtectedRoute>
    ),
  },
  {
    path: "operations/:id/edit",
    element: (
      <ProtectedRoute roles={["ADMIN", "MANAGER"]}>
        <Suspense fallback={<PageLoading />}><OperationFormPage /></Suspense>
      </ProtectedRoute>
    ),
  },
]
