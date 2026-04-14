import { useEffect, useState } from 'react'
import { Download, X } from 'lucide-react'

/**
 * InstallPrompt Component
 * Shows PWA installation prompt when available
 */
export const InstallPrompt = () => {
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null)
  const [show, setShow] = useState(false)
  const [isInstalled, setIsInstalled] = useState(false)

  useEffect(() => {
    // Check if app is already installed
    if (window.matchMedia('(display-mode: standalone)').matches) {
      setIsInstalled(true)
      return
    }

    const handleBeforeInstallPrompt = (e: any) => {
      e.preventDefault()
      setDeferredPrompt(e)
      setShow(true)
    }

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt)

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
    }
  }, [])

  const handleInstall = async () => {
    if (!deferredPrompt) return

    deferredPrompt.prompt()
    const { outcome } = await deferredPrompt.userChoice

    if (outcome === 'accepted') {
      setDeferredPrompt(null)
      setShow(false)
      setIsInstalled(true)
    }
  }

  const handleClose = () => {
    setShow(false)
  }

  if (!show || isInstalled || !deferredPrompt) return null

  return (
    <div className="fixed inset-x-0 top-0 z-50 bg-gradient-to-r from-blue-600 to-blue-700 p-4 shadow-lg">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Download className="h-5 w-5 flex-shrink-0 text-white" />
          <div className="flex-1">
            <p className="font-medium text-white">Install MedTrack</p>
            <p className="text-sm text-blue-100">
              Add to your home screen for quick access
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleInstall}
            className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-blue-600 transition-colors hover:bg-blue-50 active:bg-blue-100"
          >
            Install
          </button>
          <button
            onClick={handleClose}
            className="rounded-lg p-2 text-white transition-colors hover:bg-blue-600 active:bg-blue-500"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  )
}

export default InstallPrompt
