import { lazy, Suspense } from "react"
import { RouteObject } from "react-router-dom"

const MaterialListPage = lazy(() => import("./pages/MaterialListPage"))
const ProductListPage = lazy(() => import("./pages/ProductListPage"))
const TransactionHistoryPage = lazy(() => import("./pages/TransactionHistoryPage"))
const StockMovementPage = lazy(() => import("./pages/StockMovementPage"))
const InventoryDashboard = lazy(() => import("./pages/InventoryDashboard"))
const BatchListPage = lazy(() => import("./pages/BatchListPage"))
const StorekeeperDashboardPage = lazy(() => import("./pages/StorekeeperDashboardPage"))

// Simple fallback
const PageLoading = () => <div className="p-8 flex items-center justify-center">Loading...</div>

export const inventoryRoutes: RouteObject[] = [
  {
    path: "inventory",
    element: <Suspense fallback={<PageLoading />}><InventoryDashboard /></Suspense>,
  },
  {
    path: "inventory/materials",
    element: <Suspense fallback={<PageLoading />}><MaterialListPage /></Suspense>,
  },
  {
    path: "inventory/products",
    element: <Suspense fallback={<PageLoading />}><ProductListPage /></Suspense>,
  },
  {
    path: "inventory/transactions",
    element: <Suspense fallback={<PageLoading />}><TransactionHistoryPage /></Suspense>,
  },
  {
    path: "inventory/movements",
    element: <Suspense fallback={<PageLoading />}><StockMovementPage /></Suspense>,
  },
  {
    path: "inventory/batches",
    element: <Suspense fallback={<PageLoading />}><BatchListPage /></Suspense>,
  },
  {
    path: "inventory/storekeeper",
    element: <Suspense fallback={<PageLoading />}><StorekeeperDashboardPage /></Suspense>,
  },
]
