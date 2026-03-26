import { lazy, Suspense } from "react"
import { RouteObject, Navigate } from "react-router-dom"

const BOMListPage = lazy(() => import("./pages/BOMListPage"))
const BOMDetailPage = lazy(() => import("./pages/BOMDetailPage"))

const PageLoading = () => (
  <div className="p-8 flex items-center justify-center text-muted-foreground">
    Loading...
  </div>
)

export const bomRoutes: RouteObject[] = [
  {
    path: "bom",
    element: <Navigate to="/bom/list" replace />,
  },
  {
    path: "bom/list",
    element: (
      <Suspense fallback={<PageLoading />}>
        <BOMListPage />
      </Suspense>
    ),
  },
  {
    // Combined route: handles both /bom/new (creation) and /bom/:bomId (detail/edit)
    // MUST come before catch-all routes
    path: "bom/:bomId",
    element: (
      <Suspense fallback={<PageLoading />}>
        <BOMDetailPage />
      </Suspense>
    ),
  },
]
