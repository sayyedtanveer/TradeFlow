import { AlertTriangle } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Link } from "react-router-dom"

interface LowStockAlertProps {
  count: number
}

export function LowStockAlert({ count }: LowStockAlertProps) {
  if (count <= 0) return null

  return (
    <Alert variant="destructive" className="mb-6 bg-destructive/10 text-destructive border-destructive/20">
      <AlertTriangle className="h-5 w-5" />
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between w-full">
        <div>
          <AlertTitle className="text-base font-semibold">Low Stock Alert</AlertTitle>
          <AlertDescription>
            {count} product{count === 1 ? ' is' : 's are'} currently below the defined reorder point.
          </AlertDescription>
        </div>
        <Button variant="destructive" size="sm" asChild className="mt-4 sm:mt-0 w-max shrink-0">
          <Link to="/inventory/materials?filter=low-stock">View Materials</Link>
        </Button>
      </div>
    </Alert>
  )
}
