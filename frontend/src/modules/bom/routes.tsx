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
    // NEW: Handle creation form - must come BEFORE the dynamic :bomId route
    path: "bom/new",
    element: (
      <Suspense fallback={<PageLoading />}>
        <BOMDetailPage />
      </Suspense>
    ),
  },
  {
    // Dynamic route for viewing/editing existing BOMs
    path: "bom/:bomId",
    element: (
      <Suspense fallback={<PageLoading />}>
        <BOMDetailPage />
      </Suspense>
    ),
  },
]
