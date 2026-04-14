import { useEffect, useState } from 'react'
import { X, AlertCircle } from 'lucide-react'
import { useBarcodeScanner } from '../hooks/useBarcodeScanner'

export interface BarcodeScannerModalProps {
  isOpen: boolean
  onClose: () => void
  onScan: (barcode: string) => void
  title?: string
  description?: string
}

/**
 * BarcodeScannerModal Component
 * Modal to scan barcodes with camera
 */
export const BarcodeScannerModal = ({
  isOpen,
  onClose,
  onScan,
  title = 'Scan Barcode',
  description = 'Point camera at barcode',
}: BarcodeScannerModalProps) => {
  const [scannedValue, setScannedValue] = useState<string | null>(null)
  const [manualInput, setManualInput] = useState('')

  const { isScanning, hasPermission, usesBarcodeDetectorAPI, startScanning, stopScanning, videoRef, canvasRef } =
    useBarcodeScanner({
      onScan: (result) => {
        setScannedValue(result.value)
        onScan(result.value)
        // Auto-close after successful scan
        setTimeout(() => {
          onClose()
          setScannedValue(null)
        }, 500)
      },
      onError: (error) => {
        console.error('Scanner error:', error)
      },
    })

  useEffect(() => {
    if (isOpen) {
      startScanning()
    } else {
      stopScanning()
    }
  }, [isOpen, startScanning, stopScanning])

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (manualInput.trim()) {
      onScan(manualInput.trim())
      setManualInput('')
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40 bg-black bg-opacity-50" onClick={onClose} />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="w-full max-w-md rounded-lg bg-white shadow-xl">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
              <p className="text-sm text-gray-600">{description}</p>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <X className="h-6 w-6" />
            </button>
          </div>

          {/* Body */}
          <div className="p-6">
            {/* Permission Error */}
            {hasPermission === false && (
              <div className="mb-4 flex items-start gap-3 rounded-lg bg-red-50 p-4">
                <AlertCircle className="h-5 w-5 flex-shrink-0 text-red-600" />
                <div>
                  <h3 className="font-medium text-red-900">Camera Access Denied</h3>
                  <p className="mt-1 text-sm text-red-800">
                    Please enable camera permissions in your device settings to scan barcodes.
                  </p>
                </div>
              </div>
            )}

            {/* Video Stream */}
            {hasPermission !== false && (
              <div className="mb-4 overflow-hidden rounded-lg bg-black">
                <video
                  ref={videoRef}
                  className="aspect-video w-full object-cover"
                  playsInline
                  muted
                />
                <canvas ref={canvasRef} className="hidden" />
              </div>
            )}

            {/* Status */}
            <div className="mb-4 rounded-lg bg-blue-50 p-3 text-sm text-blue-800">
              {isScanning ? (
                <>
                  <span className="font-medium">Live scanning</span>
                  {usesBarcodeDetectorAPI ? ` (native API)` : ` (ZXing library)`}
                </>
              ) : hasPermission === false ? (
                'Camera access required'
              ) : (
                'Starting camera...'
              )}
            </div>

            {/* Scanned Result */}
            {scannedValue && (
              <div className="mb-4 rounded-lg bg-green-50 p-4">
                <p className="text-sm text-green-800">
                  <span className="font-medium">Scanned:</span> {scannedValue}
                </p>
              </div>
            )}

            {/* Manual Entry */}
            <form onSubmit={handleManualSubmit} className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Or enter barcode manually
                </label>
                <input
                  type="text"
                  value={manualInput}
                  onChange={(e) => setManualInput(e.target.value)}
                  placeholder="Type or paste barcode..."
                  className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 active:bg-gray-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!manualInput.trim()}
                  className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 active:bg-blue-800 disabled:bg-gray-400"
                >
                  Submit
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </>
  )
}

export default BarcodeScannerModal
