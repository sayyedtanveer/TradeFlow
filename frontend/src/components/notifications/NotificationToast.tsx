import React, { useEffect, useState } from 'react'
import { AlertCircle, Bell, CheckCircle, AlertTriangle, X } from 'lucide-react'
import { WebSocketNotification } from '@/hooks/useWebSocketNotifications'
import { cn } from '@/lib/utils'

interface ToastProps {
  notification: WebSocketNotification
  onClose?: () => void
  duration?: number
}

type ToastType = 'success' | 'error' | 'warning' | 'info'

const getToastType = (notificationType: string): ToastType => {
  if (notificationType.includes('FAILED') || notificationType.includes('OVERDUE')) {
    return 'error'
  }
  if (notificationType.includes('LOW_STOCK') || notificationType.includes('ALERT')) {
    return 'warning'
  }
  if (notificationType.includes('COMPLETED')) {
    return 'success'
  }
  return 'info'
}

const getToastIcon = (type: ToastType) => {
  switch (type) {
    case 'success':
      return <CheckCircle className="h-5 w-5 text-green-600" />
    case 'error':
      return <AlertCircle className="h-5 w-5 text-red-600" />
    case 'warning':
      return <AlertTriangle className="h-5 w-5 text-yellow-600" />
    case 'info':
      return <Bell className="h-5 w-5 text-blue-600" />
  }
}

const getToastStyles = (type: ToastType) => {
  switch (type) {
    case 'success':
      return 'bg-green-50 border border-green-200'
    case 'error':
      return 'bg-red-50 border border-red-200'
    case 'warning':
      return 'bg-yellow-50 border border-yellow-200'
    case 'info':
      return 'bg-blue-50 border border-blue-200'
  }
}

/**
 * Toast notification component for real-time updates.
 * Auto-dismisses after specified duration.
 */
export const NotificationToast: React.FC<ToastProps> = ({
  notification,
  onClose,
  duration = 5000,
}) => {
  const [isVisible, setIsVisible] = useState(true)
  const toastType = getToastType(notification.type)

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false)
      onClose?.()
    }, duration)

    return () => clearTimeout(timer)
  }, [duration, onClose])

  if (!isVisible) return null

  return (
    <div
      className={cn(
        'fixed bottom-4 right-4 max-w-md rounded-lg shadow-lg p-4 flex items-start gap-3 animate-in slide-in-from-bottom-2 duration-300 z-50',
        getToastStyles(toastType)
      )}
      role="alert"
    >
      <div className="flex-shrink-0 pt-0.5">{getToastIcon(toastType)}</div>

      <div className="flex-1 min-w-0">
        <h3 className={cn('font-semibold text-sm', {
          'text-green-900': toastType === 'success',
          'text-red-900': toastType === 'error',
          'text-yellow-900': toastType === 'warning',
          'text-blue-900': toastType === 'info',
        })}>
          {notification.title}
        </h3>
        <p className={cn('text-sm mt-1', {
          'text-green-800': toastType === 'success',
          'text-red-800': toastType === 'error',
          'text-yellow-800': toastType === 'warning',
          'text-blue-800': toastType === 'info',
        })}>
          {notification.message}
        </p>
      </div>

      <button
        onClick={() => {
          setIsVisible(false)
          onClose?.()
        }}
        className={cn('flex-shrink-0 mt-0.5 hover:opacity-70 transition-opacity', {
          'text-green-600': toastType === 'success',
          'text-red-600': toastType === 'error',
          'text-yellow-600': toastType === 'warning',
          'text-blue-600': toastType === 'info',
        })}
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}

/**
 * Toast container for managing multiple toasts.
 * Use this in your root layout to display real-time notifications.
 */
interface ToastContainerProps {
  notifications: WebSocketNotification[]
  onRemove?: (id: string) => void
  maxToasts?: number
}

export const NotificationToastContainer: React.FC<ToastContainerProps> = ({
  notifications,
  onRemove,
  maxToasts = 3,
}) => {
  return (
    <div className="fixed bottom-0 right-0 z-50 pointer-events-none">
      <div className="flex flex-col gap-2 p-4 pointer-events-auto">
        {notifications.slice(0, maxToasts).map((notification) => (
          <NotificationToast
            key={notification.id}
            notification={notification}
            onClose={() => onRemove?.(notification.id)}
          />
        ))}
      </div>
    </div>
  )
}

export default NotificationToast
