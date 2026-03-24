import { usePermissions } from "@/hooks/usePermissions"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ArrowDownToLine, ArrowUpToLine, ScanBarcode, UserPlus } from "lucide-react"
import { useNavigate } from "react-router-dom"

export function QuickActions() {
  const { hasRole, isAdmin } = usePermissions()
  const navigate = useNavigate()

  // Only operators/admins/managers see inventory action buttons
  const canWorkInventory = hasRole(["ADMIN", "MANAGER", "OPERATOR"])

  return (
    <Card className="col-span-1 md:col-span-4 lg:col-span-2">
      <CardHeader>
        <CardTitle>Quick Actions</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
        {canWorkInventory && (
          <>
            <Button
              className="w-full justify-start h-12"
              variant="outline"
              onClick={() => navigate("/inventory/products?action=scan")}
            >
              <ScanBarcode className="mr-2 h-5 w-5 text-primary" />
              Scan Barcode
            </Button>
            <Button
              className="w-full justify-start h-12"
              variant="outline"
              onClick={() => navigate("/inventory/movements/add")}
            >
              <ArrowDownToLine className="mr-2 h-5 w-5 text-emerald-500" />
              Receive Goods
            </Button>
            <Button
              className="w-full justify-start h-12"
              variant="outline"
              onClick={() => navigate("/inventory/movements/issue")}
            >
              <ArrowUpToLine className="mr-2 h-5 w-5 text-amber-500" />
              Issue Material
            </Button>
          </>
        )}
        
        {isAdmin() && (
          <Button
            className="w-full justify-start h-12"
            variant="outline"
            onClick={() => navigate("/users/new")}
          >
            <UserPlus className="mr-2 h-5 w-5 text-purple-500" />
            Add User
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
