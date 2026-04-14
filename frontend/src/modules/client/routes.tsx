import type { RouteObject } from "react-router-dom"
import ClientLayout from "./components/ClientLayout"
import ClientProtectedRoute from "./components/ClientProtectedRoute"
import ClientDashboard from "./pages/ClientDashboard"
import ClientLogin from "./pages/ClientLogin"
import CreditStatus from "./pages/CreditStatus"
import InvoicesList from "./pages/InvoicesList"
import OrderDetail from "./pages/OrderDetail"
import OrdersList from "./pages/OrdersList"
import Profile from "./pages/Profile"
import Reorder from "./pages/Reorder"
import Support from "./pages/Support"

export const clientRoutes: RouteObject[] = [
  {
    path: "/client/login",
    element: <ClientLogin />,
  },
  {
    path: "/client",
    element: <ClientProtectedRoute />,
    children: [
      {
        element: <ClientLayout />,
        children: [
          { index: true, element: <ClientDashboard /> },
          { path: "orders", element: <OrdersList /> },
          { path: "orders/:id", element: <OrderDetail /> },
          { path: "invoices", element: <InvoicesList /> },
          { path: "reorder", element: <Reorder /> },
          { path: "credit", element: <CreditStatus /> },
          { path: "profile", element: <Profile /> },
          { path: "support", element: <Support /> },
        ],
      },
    ],
  },
]
