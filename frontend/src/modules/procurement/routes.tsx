import { RouteObject } from "react-router-dom"
import ProcurementHubPage from "./pages/ProcurementHubPage"
import SuppliersListPage from "./pages/SuppliersListPage"
import PurchaseOrdersPage from "./pages/PurchaseOrdersPage"
import PurchaseOrderDetailPage from "./pages/PurchaseOrderDetailPage"
import GrnPage from "./pages/GrnPage"
import QualityModulePage from "./pages/QualityModulePage"
import MaterialRequestsPage from "./pages/MaterialRequestsPage"
import SubcontractListPage from "./pages/SubcontractListPage"
import SubcontractOrderDetailPage from "./pages/SubcontractOrderDetailPage"
import SupplierPortalPage from "./pages/SupplierPortalPage"
import SupplierPortalPoDetailPage from "./pages/SupplierPortalPoDetailPage"
import RFQListPage from "./pages/RFQListPage"
import RFQCreatePage from "./pages/RFQCreatePage"
import RFQDetailPage from "./pages/RFQDetailPage"
import SupplierPerformancePage from "./pages/SupplierPerformancePage"

export const procurementRoutes: RouteObject[] = [
  { path: "procurement", element: <ProcurementHubPage /> },
  { path: "procurement/suppliers", element: <SuppliersListPage /> },
  { path: "procurement/purchase-orders", element: <PurchaseOrdersPage /> },
  { path: "procurement/purchase-orders/:poId", element: <PurchaseOrderDetailPage /> },
  { path: "procurement/grn", element: <GrnPage /> },
  { path: "procurement/quality", element: <QualityModulePage /> },
  { path: "procurement/mrp", element: <MaterialRequestsPage /> },
  { path: "procurement/subcontract", element: <SubcontractListPage /> },
  { path: "procurement/subcontract/:orderId", element: <SubcontractOrderDetailPage /> },
  // ── RFQ ──────────────────────────────────────────────────────────────
  { path: "procurement/rfq", element: <RFQListPage /> },
  { path: "procurement/rfq/new", element: <RFQCreatePage /> },
  { path: "procurement/rfq/:rfqId", element: <RFQDetailPage /> },
  // ── Supplier performance ──────────────────────────────────────────────
  { path: "procurement/supplier-performance", element: <SupplierPerformancePage /> },
  // ── Supplier portal ───────────────────────────────────────────────────
  { path: "supplier-portal", element: <SupplierPortalPage /> },
  { path: "supplier-portal/po/:poId", element: <SupplierPortalPoDetailPage /> },
]
