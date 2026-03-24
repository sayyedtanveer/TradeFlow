import { lazy, Suspense } from "react"
import { RouteObject, Navigate } from "react-router-dom"

const MaterialListPage = lazy(() => import("./pages/MaterialListPage"))
const TransactionHistoryPage = lazy(() => import("./pages/TransactionHistoryPage"))

// Simple fallback
const PageLoading = () => <div className="p-8 flex items-center justify-center">Loading...</div>

export const inventoryRoutes: RouteObject[] = [
  {
    path: "inventory",
    element: <Navigate to="/inventory/materials" replace />,
  },
  {
    path: "inventory/materials",
    element: <Suspense fallback={<PageLoading />}><MaterialListPage /></Suspense>,
  },
  {
    path: "inventory/transactions",
    element: <Suspense fallback={<PageLoading />}><TransactionHistoryPage /></Suspense>,
  },
]
