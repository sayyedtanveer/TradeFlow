import { useState } from "react"
import { Outlet } from "react-router-dom"
import { Barcode } from "lucide-react"
import { Toaster } from "@/components/ui/toaster"
import { OfflineIndicator } from "@/components/offline/OfflineIndicator"
import { BottomNavigation } from "@/components/navigation/BottomNavigation"
import { FloatingActionButton } from "@/components/mobile/FloatingActionButton"
import { BarcodeScannerModal } from "@/components/barcode/BarcodeScannerModal"
import { InstallPrompt } from "@/components/pwa/InstallPrompt"

export function AppLayout() {
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
    <>
      {/* Main page content */}
      <Outlet />

      {/* Global Providers */}
      <Toaster />
      <OfflineIndicator />
      <BottomNavigation />
      <InstallPrompt />
      
      {/* Floating Action Button - Barcode Scanner */}
      <FloatingActionButton
        icon={Barcode}
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
    </>
  )
}
