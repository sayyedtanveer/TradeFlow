import { lazy, Suspense } from "react"
import type { RouteObject } from "react-router-dom"

const FinanceDashboardPage = lazy(() => import("./pages/FinanceDashboardPage"))
const ReportsPage = lazy(() => import("./pages/ReportsPage"))
const NewInvoicePage = lazy(() => import("./pages/NewInvoicePage"))
const NewSupplierInvoicePage = lazy(() => import("./pages/NewSupplierInvoicePage"))

const PageLoading = () => (
  <div className="flex h-64 items-center justify-center text-slate-400">
    <div className="flex items-center gap-2">
      <div className="w-4 h-4 rounded-full bg-blue-500 animate-bounce" />
      <div className="w-4 h-4 rounded-full bg-blue-500 animate-bounce [animation-delay:0.1s]" />
      <div className="w-4 h-4 rounded-full bg-blue-500 animate-bounce [animation-delay:0.2s]" />
    </div>
  </div>
)

export const financeRoutes: RouteObject[] = [
  {
    path: "finance",
    element: (
      <Suspense fallback={<PageLoading />}>
        <FinanceDashboardPage />
      </Suspense>
    ),
  },
  {
    path: "finance/invoices",
    element: (
      <Suspense fallback={<PageLoading />}>
        <FinanceDashboardPage />
      </Suspense>
    ),
  },
  {
    path: "finance/invoices/new",
    element: (
      <Suspense fallback={<PageLoading />}>
        <NewInvoicePage />
      </Suspense>
    ),
  },
  {
    path: "finance/supplier-invoices",
    element: (
      <Suspense fallback={<PageLoading />}>
        <FinanceDashboardPage />
      </Suspense>
    ),
  },
  {
    path: "finance/supplier-invoices/new",
    element: (
      <Suspense fallback={<PageLoading />}>
        <NewSupplierInvoicePage />
      </Suspense>
    ),
  },
  {
    path: "reports",
    element: (
      <Suspense fallback={<PageLoading />}>
        <ReportsPage />
      </Suspense>
    ),
  },
]
