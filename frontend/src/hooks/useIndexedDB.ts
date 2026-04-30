import { useState, useCallback, useEffect, useRef } from 'react'

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
  const storesKey = JSON.stringify(config.stores)
  const dbRef = useRef<IDBDatabase | null>(null)
  const readyPromiseRef = useRef<Promise<IDBDatabase> | null>(null)
  const resolveReadyRef = useRef<((database: IDBDatabase) => void) | null>(null)
  const rejectReadyRef = useRef<((reason?: unknown) => void) | null>(null)

  // Initialize IndexedDB
  useEffect(() => {
    const initDB = async () => {
      setDb(null)
      setIsReady(false)
      setError(null)
      dbRef.current = null
      readyPromiseRef.current = new Promise<IDBDatabase>((resolve, reject) => {
        resolveReadyRef.current = resolve
        rejectReadyRef.current = reject
      })

      try {
        const request = indexedDB.open(config.dbName, config.version)

        request.onerror = () => {
          const err = request.error?.message || 'Failed to open IndexedDB'
          setError(err)
          rejectReadyRef.current?.(new Error(err))
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
          dbRef.current = request.result
          setDb(request.result)
          setIsReady(true)
          setError(null)
          resolveReadyRef.current?.(request.result)
        }
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : String(err)
        setError(errorMsg)
        rejectReadyRef.current?.(new Error(errorMsg))
      }
    }

    void initDB()

    return () => {
      // Cleanup on unmount
      if (dbRef.current) {
        dbRef.current.close()
        dbRef.current = null
      }
    }
  }, [config.dbName, config.version, storesKey])

  const getDatabase = useCallback(async (): Promise<IDBDatabase> => {
    if (dbRef.current) {
      return dbRef.current
    }
    if (!readyPromiseRef.current) {
      throw new Error('IndexedDB initialization not started')
    }
    return readyPromiseRef.current
  }, [])

  // Add item to store
  const add = useCallback(
    async (storeName: string, item: StoredEntity): Promise<void> => {
      const database = await getDatabase()

      return new Promise((resolve, reject) => {
        const transaction = database.transaction([storeName], 'readwrite')
        const store = transaction.objectStore(storeName)
        const request = store.add(item)

        request.onerror = () => reject(request.error)
        request.onsuccess = () => resolve()
      })
    },
    [getDatabase]
  )

  // Update item in store
  const update = useCallback(
    async (storeName: string, item: StoredEntity): Promise<void> => {
      const database = await getDatabase()

      return new Promise((resolve, reject) => {
        const transaction = database.transaction([storeName], 'readwrite')
        const store = transaction.objectStore(storeName)
        const request = store.put(item)

        request.onerror = () => reject(request.error)
        request.onsuccess = () => resolve()
      })
    },
    [getDatabase]
  )

  // Get item by ID
  const get = useCallback(
    async (storeName: string, id: string): Promise<StoredEntity | null> => {
      const database = await getDatabase()

      return new Promise((resolve, reject) => {
        const transaction = database.transaction([storeName], 'readonly')
        const store = transaction.objectStore(storeName)
        const request = store.get(id)

        request.onerror = () => reject(request.error)
        request.onsuccess = () => resolve(request.result || null)
      })
    },
    [getDatabase]
  )

  // Get all items from store
  const getAll = useCallback(
    async (storeName: string): Promise<StoredEntity[]> => {
      const database = await getDatabase()

      return new Promise((resolve, reject) => {
        const transaction = database.transaction([storeName], 'readonly')
        const store = transaction.objectStore(storeName)
        const request = store.getAll()

        request.onerror = () => reject(request.error)
        request.onsuccess = () => resolve(request.result)
      })
    },
    [getDatabase]
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
      const database = await getDatabase()

      return new Promise((resolve, reject) => {
        const transaction = database.transaction([storeName], 'readwrite')
        const store = transaction.objectStore(storeName)
        const request = store.delete(id)

        request.onerror = () => reject(request.error)
        request.onsuccess = () => resolve()
      })
    },
    [getDatabase]
  )

  // Clear entire store
  const clear = useCallback(
    async (storeName: string): Promise<void> => {
      const database = await getDatabase()

      return new Promise((resolve, reject) => {
        const transaction = database.transaction([storeName], 'readwrite')
        const store = transaction.objectStore(storeName)
        const request = store.clear()

        request.onerror = () => reject(request.error)
        request.onsuccess = () => resolve()
      })
    },
    [getDatabase]
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
