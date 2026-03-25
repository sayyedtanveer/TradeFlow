import { createBrowserRouter } from "react-router-dom"
import { lazy, Suspense } from "react"
import { ProtectedRoute } from "./ProtectedRoute"
import AuthLayout from "@/layouts/AuthLayout"
import DefaultLayout from "@/layouts/DefaultLayout"
import { inventoryRoutes } from "@/modules/inventory/routes"
import { usersRoutes } from "@/modules/users/routes"
import { bomRoutes } from "@/modules/bom/routes"
import { NotFoundPage, ForbiddenPage } from "@/components/layout/ErrorPages"

// Lazy loaded modules
const LoginPage = lazy(() => import("@/modules/auth/pages/LoginPage"))
const RegisterTenantPage = lazy(() => import("@/modules/auth/pages/RegisterTenantPage"))
const DashboardPage = lazy(() => import("@/modules/dashboard/pages/DashboardPage"))

// Loading fallback for Suspense
const PageLoading = () => <div className="p-8 flex items-center justify-center">Loading...</div>

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <AuthLayout />,
    children: [
      { index: true, element: <Suspense fallback={<PageLoading />}><LoginPage /></Suspense> },
    ],
  },
  {
    path: "/register",
    element: <AuthLayout />,
    children: [
      { index: true, element: <Suspense fallback={<PageLoading />}><RegisterTenantPage /></Suspense> },
    ],
  },
  {
    path: "/",
    element: <ProtectedRoute />, // All child routes require auth
    children: [
      {
        path: "/",
        element: <DefaultLayout />,
        children: [
          { index: true, element: <Suspense fallback={<PageLoading />}><DashboardPage /></Suspense> },
          ...inventoryRoutes,
          ...usersRoutes,
          ...bomRoutes,
          { path: "403", element: <ForbiddenPage /> },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
])
