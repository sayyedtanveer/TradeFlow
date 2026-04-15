import { useEffect, useState } from 'react'
import { AlertCircle, Check, Loader2, Wifi, WifiOff } from 'lucide-react'
import { useOfflineSync } from '../../hooks/useOfflineSync'

/**
 * OfflineIndicator Component
 * Shows network status, pending sync count, and last sync time
 */
export const OfflineIndicator = () => {
  const { pendingCount, isSyncing, lastSyncTime, syncError, isOnline, syncAll } = useOfflineSync()
  const [show, setShow] = useState(false)

  useEffect(() => {
    // Show indicator if offline or pending items
    setShow(!isOnline || pendingCount > 0)
  }, [isOnline, pendingCount])

  if (!show) return null

  const handleManualSync = async () => {
    await syncAll()
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 border-t border-gray-200 bg-white shadow-lg">
      <div className="mx-auto max-w-7xl px-4 py-3">
        <div className="flex items-center justify-between gap-4">
          {/* Status Section */}
          <div className="flex items-center gap-3">
            {isOnline ? (
              <div className="flex items-center gap-2 text-green-600">
                <Wifi className="h-5 w-5" />
                <span className="text-sm font-medium">Online</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-amber-600">
                <WifiOff className="h-5 w-5" />
                <span className="text-sm font-medium">Offline</span>
              </div>
            )}

            {/* Pending Count */}
            {pendingCount > 0 && (
              <div className="flex items-center gap-2 rounded-full bg-amber-50 px-3 py-1">
                <AlertCircle className="h-4 w-4 text-amber-600" />
                <span className="text-sm text-amber-900">
                  {pendingCount} pending {pendingCount === 1 ? 'change' : 'changes'}
                </span>
              </div>
            )}
          </div>

          {/* Info Section */}
          <div className="flex flex-1 flex-col items-end gap-1">
            {lastSyncTime && !isSyncing && (
              <span className="text-xs text-gray-500">
                Last synced: {formatTime(lastSyncTime)}
              </span>
            )}

            {syncError && (
              <span className="text-xs text-red-600">{syncError}</span>
            )}
          </div>

          {/* Action Section */}
          <div className="flex items-center gap-2">
            {isSyncing ? (
              <div className="flex items-center gap-2 rounded bg-blue-50 px-3 py-1">
                <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                <span className="text-sm text-blue-600">Syncing...</span>
              </div>
            ) : pendingCount > 0 && isOnline ? (
              <button
                onClick={handleManualSync}
                className="rounded bg-blue-50 px-3 py-1 text-sm font-medium text-blue-600 transition-colors hover:bg-blue-100 active:bg-blue-200"
              >
                Sync Now
              </button>
            ) : pendingCount === 0 && isOnline ? (
              <div className="flex items-center gap-2 text-green-600">
                <Check className="h-4 w-4" />
                <span className="text-sm font-medium">All synced</span>
              </div>
            ) : null}
          </div>
        </div>

        {/* Error Message */}
        {syncError && (
          <div className="mt-2 rounded bg-red-50 p-2 text-sm text-red-700">
            {syncError}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Format relative time
 */
function formatTime(date: Date): string {
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days < 7) return `${days}d ago`

  return date.toLocaleDateString()
}

export default OfflineIndicator
