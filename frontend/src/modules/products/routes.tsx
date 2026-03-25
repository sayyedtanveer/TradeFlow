import { RouteObject } from "react-router-dom"
import { lazy, Suspense } from "react"
import { ProtectedRoute } from "@/app/routes/ProtectedRoute"

const ProductTemplateListPage = lazy(() => import("./pages/ProductTemplateListPage"))
const ProductTemplateFormPage = lazy(() => import("./pages/ProductTemplateFormPage"))

const PageLoading = () => <div className="p-8 flex items-center justify-center">Loading...</div>

export const productRoutes: RouteObject[] = [
  {
    path: "products",
    element: <ProtectedRoute allowedRoles={["ADMIN", "MANAGER"]} />,
    children: [
      {
        index: true,
        element: (
          <Suspense fallback={<PageLoading />}>
            <ProductTemplateListPage />
          </Suspense>
        ),
      },
      {
        path: "new",
        element: (
          <Suspense fallback={<PageLoading />}>
            <ProductTemplateFormPage />
          </Suspense>
        ),
      },
      {
        path: ":id",
        element: (
          <Suspense fallback={<PageLoading />}>
            <ProductTemplateFormPage />
          </Suspense>
        ),
      },
    ],
  },
]
