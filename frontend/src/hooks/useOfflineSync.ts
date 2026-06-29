import { useState, useCallback, useEffect } from 'react'
import { useIndexedDB } from './useIndexedDB'

export interface SyncQueueItem {
  id: string
  action: string // 'issue_material', 'receive_goods', 'complete_operation', etc.
  resource: string // 'work_order', 'material', etc.
  resourceId: string
  data: Record<string, any>
  timestamp: number
  retries: number
  maxRetries: number
  synced: boolean
}

export interface SyncOptions {
  maxRetries?: number
  retryDelay?: number // ms between retries
  autoSync?: boolean
}

/**
 * Hook for managing offline sync queue.
 * Queues operations when offline, syncs when online.
 */
export const useOfflineSync = (options: SyncOptions = {}) => {
  const {
    maxRetries = 3,
    retryDelay = 5000,
    autoSync = true,
  } = options

  const [pendingCount, setPendingCount] = useState(0)
  const [isSyncing, setIsSyncing] = useState(false)
  const [lastSyncTime, setLastSyncTime] = useState<Date | null>(null)
  const [syncError, setSyncError] = useState<string | null>(null)

  const idb = useIndexedDB({
    dbName: 'MedTrackOffline',
    version: 1,
    stores: {
      syncQueue: 'id',
      cachedData: 'id',
      workOrders: 'id',
      materials: 'id',
      boms: 'id',
    },
  })

  // Update pending count
  const updatePendingCount = useCallback(async () => {
    if (!idb.isReady) {
      setPendingCount(0)
      return
    }

    try {
      const unsynced = await idb.getAllUnsynced('syncQueue')
      setPendingCount(unsynced.length)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      setSyncError(errorMsg)
      setPendingCount(0)
    }
  }, [idb])

  // Queue an action for sync
  const queueAction = useCallback(
    async (
      action: string,
      resource: string,
      resourceId: string,
      data: Record<string, any>
    ): Promise<string> => {
      const queueItem: SyncQueueItem = {
        id: `${action}-${resource}-${Date.now()}`,
        action,
        resource,
        resourceId,
        data,
        timestamp: Date.now(),
        retries: 0,
        maxRetries,
        synced: false,
      }

      await idb.add('syncQueue', queueItem as any)
      await updatePendingCount()

      return queueItem.id
    },
    [idb, maxRetries, updatePendingCount]
  )

  // Sync a single item
  const syncItem = useCallback(
    async (item: SyncQueueItem): Promise<boolean> => {
      try {
        // Construct API endpoint based on action
        const endpoint = getEndpointForAction(item.action, item.resource)
        
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...item.data,
            resourceId: item.resourceId,
          }),
        })

        if (!response.ok) {
          throw new Error(`API error: ${response.status}`)
        }

        // Mark as synced
        const synced: SyncQueueItem = {
          ...item,
          synced: true,
        }
        await idb.update('syncQueue', synced as any)
        return true
      } catch (err) {
        // Increment retry count
        const updated: SyncQueueItem = {
          ...item,
          retries: item.retries + 1,
        }

        if (item.retries < item.maxRetries) {
          await idb.update('syncQueue', updated as any)
          return false
        } else {
          // Max retries exceeded, mark as failed
          await idb.delete('syncQueue', item.id)
          return false
        }
      }
    },
    [idb]
  )

  // Sync all pending items
  const syncAll = useCallback(async (): Promise<number> => {
    if (!idb.isReady || !navigator.onLine) {
      return 0
    }

    setIsSyncing(true)
    setSyncError(null)

    try {
      const unsynced = await idb.getAllUnsynced('syncQueue')
      let syncedCount = 0

      for (const item of unsynced) {
        const success = await syncItem(item as SyncQueueItem)
        if (success) syncedCount++

        // Add delay between retries
        if (!success && unsynced.indexOf(item) < unsynced.length - 1) {
          await new Promise((resolve) => setTimeout(resolve, retryDelay))
        }
      }

      setLastSyncTime(new Date())
      await updatePendingCount()
      return syncedCount
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      setSyncError(errorMsg)
      return 0
    } finally {
      setIsSyncing(false)
    }
  }, [idb, syncItem, retryDelay, updatePendingCount])

  // Auto-sync when online
  useEffect(() => {
    if (!autoSync || !idb.isReady) return

    const handleOnline = () => {
      void syncAll()
    }

    const handleOffline = () => {
      setSyncError('Currently offline. Changes will sync when reconnected.')
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [autoSync, idb.isReady, syncAll])

  // Initial pending count
  useEffect(() => {
    if (!idb.isReady) {
      return
    }

    void updatePendingCount()
  }, [idb.isReady, updatePendingCount])

  useEffect(() => {
    if (idb.error) {
      setSyncError(idb.error)
    }
  }, [idb.error])

  // Cache work order data
  const cacheWorkOrder = useCallback(
    async (id: string, data: any) => {
      await idb.update('workOrders', {
        id,
        data,
        timestamp: Date.now(),
        synced: true,
      })
    },
    [idb]
  )

  // Get cached work order
  const getCachedWorkOrder = useCallback(
    async (id: string) => {
      const item = await idb.get('workOrders', id)
      return item?.data || null
    },
    [idb]
  )

  // Cache material data
  const cacheMaterial = useCallback(
    async (id: string, data: any) => {
      await idb.update('materials', {
        id,
        data,
        timestamp: Date.now(),
        synced: true,
      })
    },
    [idb]
  )

  // Get cached material
  const getCachedMaterial = useCallback(
    async (id: string) => {
      const item = await idb.get('materials', id)
      return item?.data || null
    },
    [idb]
  )

  return {
    // State
    pendingCount,
    isSyncing,
    lastSyncTime,
    syncError,
    isOnline: navigator.onLine,

    // Queue operations
    queueAction,
    syncAll,
    updatePendingCount,

    // Cache operations
    cacheWorkOrder,
    getCachedWorkOrder,
    cacheMaterial,
    getCachedMaterial,

    // Direct IDB access
    idb,
  }
}

/**
 * Map action names to API endpoints
 */
function getEndpointForAction(action: string, _resource: string): string {
  switch (action) {
    case 'receive_goods':
      return `/api/v1/supply-chain/grn`
    default:
      return '/api/v1/unknown'
  }
}

export default useOfflineSync
