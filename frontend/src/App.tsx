import { useState } from "react"
import { RouterProvider } from "react-router-dom"
import { BarCode } from "lucide-react"
import { router } from "@/app/routes"
import { QueryProvider } from "@/app/providers/QueryProvider"
import { ErrorBoundary } from "@/components/layout/ErrorBoundary"
import { Toaster } from "@/components/ui/toaster"
import { OfflineIndicator } from "@/components/offline/OfflineIndicator"
import { BottomNavigation } from "@/components/navigation/BottomNavigation"
import { FloatingActionButton } from "@/components/mobile/FloatingActionButton"
import { BarcodeScannerModal } from "@/components/barcode/BarcodeScannerModal"
import { InstallPrompt } from "@/components/pwa/InstallPrompt"

export default function App() {
  const [scannerOpen, setScannerOpen] = useState(false)

  const handleBarcodeScan = (barcode: string) => {
    // Log the scanned barcode - can be extended to route to specific handlers
    console.log("Scanned barcode:", barcode)
    // TODO: Implement barcode action routing
    // - If material code: show stock and location
    // - If work order code: show requirements and operations
    // - If product code: show inventory details
  }

  return (
    <ErrorBoundary>
      <QueryProvider>
        <RouterProvider router={router} />
        
        {/* Global Providers */}
        <Toaster />
        <OfflineIndicator />
        <BottomNavigation />
        <InstallPrompt />
        
        {/* Floating Action Button - Barcode Scanner */}
        <FloatingActionButton
          icon={BarCode}
          label="Scan"
          onClick={() => setScannerOpen(true)}
        />
        
        {/* Barcode Scanner Modal */}
        <BarcodeScannerModal
          isOpen={scannerOpen}
          onClose={() => setScannerOpen(false)}
          onScan={handleBarcodeScan}
          title="Scan Work Order or Material"
          description="Point camera at barcode"
        />
      </QueryProvider>
    </ErrorBoundary>
  )
}
