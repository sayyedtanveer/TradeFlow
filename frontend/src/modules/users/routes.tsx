import { lazy, Suspense } from "react"
import { RouteObject } from "react-router-dom"

const UserListPage = lazy(() => import("./pages/UserListPage"))

// Simple fallback
const PageLoading = () => <div className="p-8 flex items-center justify-center">Loading...</div>

export const usersRoutes: RouteObject[] = [
  {
    path: "users",
    element: <Suspense fallback={<PageLoading />}><UserListPage /></Suspense>,
  },
]
