import { useState, useCallback, useEffect } from 'react'

export interface IndexedDBConfig {
  dbName: string
  version: number
  stores: Record<string, string> // storeName -> keyPath
}

export interface StoredEntity {
  id: string
  data: any
  timestamp: number
  synced: boolean
}

/**
 * Hook for IndexedDB operations (offline storage).
 * Handles read/write of cached data and offline queue items.
 */
export const useIndexedDB = (config: IndexedDBConfig) => {
  const [db, setDb] = useState<IDBDatabase | null>(null)
  const [isReady, setIsReady] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Initialize IndexedDB
  useEffect(() => {
    const initDB = async () => {
      try {
        const request = indexedDB.open(config.dbName, config.version)

        request.onerror = () => {
          const err = request.error?.message || 'Failed to open IndexedDB'
          setError(err)
        }

        request.onupgradeneeded = (event) => {
          const db = (event.target as IDBOpenDBRequest).result
          
          // Create object stores
          for (const [storeName, keyPath] of Object.entries(config.stores)) {
            if (!db.objectStoreNames.contains(storeName)) {
              db.createObjectStore(storeName, { keyPath })
            }
          }
        }

        request.onsuccess = () => {
          setDb(request.result)
          setIsReady(true)
          setError(null)
        }
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : String(err)
        setError(errorMsg)
      }
    }

    initDB()

    return () => {
      // Cleanup on unmount
      if (db) {
        db.close()
      }
    }
  }, [config.dbName, config.version, config.stores])

  // Add item to store
  const add = useCallback(
    async (storeName: string, item: StoredEntity): Promise<void> => {
      if (!db) throw new Error('IndexedDB not initialized')

      return new Promise((resolve, reject) => {
        const transaction = db.transaction([storeName], 'readwrite')
        const store = transaction.objectStore(storeName)
        const request = store.add(item)

        request.onerror = () => reject(request.error)
        request.onsuccess = () => resolve()
      })
    },
    [db]
  )

  // Update item in store
  const update = useCallback(
    async (storeName: string, item: StoredEntity): Promise<void> => {
      if (!db) throw new Error('IndexedDB not initialized')

      return new Promise((resolve, reject) => {
        const transaction = db.transaction([storeName], 'readwrite')
        const store = transaction.objectStore(storeName)
        const request = store.put(item)

        request.onerror = () => reject(request.error)
        request.onsuccess = () => resolve()
      })
    },
    [db]
  )

  // Get item by ID
  const get = useCallback(
    async (storeName: string, id: string): Promise<StoredEntity | null> => {
      if (!db) throw new Error('IndexedDB not initialized')

      return new Promise((resolve, reject) => {
        const transaction = db.transaction([storeName], 'readonly')
        const store = transaction.objectStore(storeName)
        const request = store.get(id)

        request.onerror = () => reject(request.error)
        request.onsuccess = () => resolve(request.result || null)
      })
    },
    [db]
  )

  // Get all items from store
  const getAll = useCallback(
    async (storeName: string): Promise<StoredEntity[]> => {
      if (!db) throw new Error('IndexedDB not initialized')

      return new Promise((resolve, reject) => {
        const transaction = db.transaction([storeName], 'readonly')
        const store = transaction.objectStore(storeName)
        const request = store.getAll()

        request.onerror = () => reject(request.error)
        request.onsuccess = () => resolve(request.result)
      })
    },
    [db]
  )

  // Get all unsynced items
  const getAllUnsynced = useCallback(
    async (storeName: string): Promise<StoredEntity[]> => {
      const allItems = await getAll(storeName)
      return allItems.filter((item) => !item.synced)
    },
    [getAll]
  )

  // Delete item
  const delete_ = useCallback(
    async (storeName: string, id: string): Promise<void> => {
      if (!db) throw new Error('IndexedDB not initialized')

      return new Promise((resolve, reject) => {
        const transaction = db.transaction([storeName], 'readwrite')
        const store = transaction.objectStore(storeName)
        const request = store.delete(id)

        request.onerror = () => reject(request.error)
        request.onsuccess = () => resolve()
      })
    },
    [db]
  )

  // Clear entire store
  const clear = useCallback(
    async (storeName: string): Promise<void> => {
      if (!db) throw new Error('IndexedDB not initialized')

      return new Promise((resolve, reject) => {
        const transaction = db.transaction([storeName], 'readwrite')
        const store = transaction.objectStore(storeName)
        const request = store.clear()

        request.onerror = () => reject(request.error)
        request.onsuccess = () => resolve()
      })
    },
    [db]
  )

  return {
    isReady,
    error,
    db,
    add,
    update,
    get,
    getAll,
    getAllUnsynced,
    delete: delete_,
    clear,
  }
}

export default useIndexedDB
