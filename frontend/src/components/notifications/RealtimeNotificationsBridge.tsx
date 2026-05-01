import { useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from '@/hooks/use-toast'
import { useWebSocketNotifications, type WebSocketNotification } from '@/hooks/useWebSocketNotifications'

export const REALTIME_EVENT_NAME = 'erp:realtime'

export function RealtimeNotificationsBridge() {
  const queryClient = useQueryClient()

  const handleNotification = useCallback((notification: WebSocketNotification) => {
    window.dispatchEvent(new CustomEvent(REALTIME_EVENT_NAME, { detail: notification }))
    void queryClient.invalidateQueries()

    toast({
      title: notification.title,
      description: notification.message,
    })
  }, [queryClient])

  useWebSocketNotifications({
    onNotification: handleNotification,
  })

  return null
}
