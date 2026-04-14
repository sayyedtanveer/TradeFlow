import { RouteObject } from "react-router-dom"
import CapacityLoadChart from "./pages/CapacityLoadChart"
import MRPDashboard from "./pages/MRPDashboard"

export const mrpRoutes: RouteObject[] = [
  { path: "mrp", element: <MRPDashboard /> },
  { path: "mrp/capacity", element: <CapacityLoadChart /> },
]
