import React, { useState, useEffect } from 'react'
import { Bell, X } from 'lucide-react'
import { useWebSocketNotifications, WebSocketNotification } from '@/hooks/useWebSocketNotifications'
import { cn } from '@/lib/utils'

/**
 * RealtimeBell component displays real-time notifications.
 *
 * Features:
 * - Shows notification count on bell icon
 * - Dropdown menu with recent notifications
 * - Visual indicators for different notification types
 * - Click outside to close dropdown
 * - Clear notifications button
 */
export const RealtimeBell: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)
  const [hasShaken, setHasShaken] = useState(false)
  const { notifications, isConnected } = useWebSocketNotifications()

  // Update unread count
  useEffect(() => {
    setUnreadCount(notifications.length)
  }, [notifications])

  // Trigger shake animation on new notification
  useEffect(() => {
    if (notifications.length > 0) {
      setHasShaken(true)
      setTimeout(() => setHasShaken(false), 600)
    }
  }, [notifications.length])

  // Close dropdown on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false)
      }
    }
    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
      return () => document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen])

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (!target.closest('[data-notification-bell]')) {
        setIsOpen(false)
      }
    }
    if (isOpen) {
      document.addEventListener('click', handleClickOutside)
      return () => document.removeEventListener('click', handleClickOutside)
    }
  }, [isOpen])

  const getNotificationColor = (type: string) => {
    switch (type) {
      case 'ORDER_STATUS_CHANGED':
        return 'border-l-blue-500 bg-blue-50'
      case 'LOW_STOCK':
        return 'border-l-orange-500 bg-orange-50'
      case 'WORK_ORDER_RELEASED':
      case 'WORK_ORDER_STARTED':
      case 'WORK_ORDER_COMPLETED':
        return 'border-l-purple-500 bg-purple-50'
      case 'INVOICE_OVERDUE':
        return 'border-l-red-500 bg-red-50'
      case 'QUALITY_INSPECTION_FAILED':
        return 'border-l-red-600 bg-red-50'
      default:
        return 'border-l-gray-500 bg-gray-50'
    }
  }

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'ORDER_STATUS_CHANGED':
        return '📦'
      case 'LOW_STOCK':
        return '⚠️'
      case 'WORK_ORDER_RELEASED':
      case 'WORK_ORDER_STARTED':
      case 'WORK_ORDER_COMPLETED':
        return '🏭'
      case 'INVOICE_OVERDUE':
        return '💰'
      case 'QUALITY_INSPECTION_FAILED':
        return '❌'
      default:
        return '🔔'
    }
  }

  const formatTime = (isoString: string) => {
    const date = new Date(isoString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMinutes = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMinutes < 1) return 'Just now'
    if (diffMinutes < 60) return `${diffMinutes}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`

    return date.toLocaleDateString()
  }

  return (
    <div className="relative" data-notification-bell>
      {/* Bell Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'relative p-2 text-gray-600 hover:text-gray-900 transition-colors',
          hasShaken && 'animate-bounce',
          isConnected ? 'hover:bg-gray-100 rounded-full' : 'opacity-60'
        )}
        aria-label="Notifications"
        title={isConnected ? 'Connected' : 'Disconnected'}
      >
        <Bell className="h-5 w-5" />

        {/* Status Dot */}
        <div
          className={cn(
            'absolute top-1 right-1 h-2 w-2 rounded-full animate-pulse',
            isConnected ? 'bg-green-500' : 'bg-gray-400'
          )}
        />

        {/* Unread Count Badge */}
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white transform translate-x-1/2 -translate-y-1/2 bg-red-600 rounded-full min-w-[20px]">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 z-50 w-96 mt-2 bg-white rounded-lg shadow-lg border border-gray-200 max-h-96 overflow-hidden flex flex-col animate-in fade-in slide-in-from-top-2 duration-200">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
            <h3 className="text-sm font-semibold text-gray-900">Notifications</h3>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
                  {unreadCount} new
                </span>
              )}
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 hover:bg-gray-200 rounded hover:text-gray-600 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Notifications List */}
          <div className="overflow-y-auto flex-1">
            {notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <Bell className="h-8 w-8 text-gray-300 mb-2" />
                <p className="text-sm text-gray-500">No notifications yet</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {notifications.slice(0, 10).map((notification: WebSocketNotification) => (
                  <div
                    key={notification.id}
                    className={cn(
                      'px-4 py-3 hover:bg-gray-50 transition-colors border-l-4 cursor-pointer',
                      getNotificationColor(notification.type)
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <span className="text-lg flex-shrink-0 mt-1">
                        {getNotificationIcon(notification.type)}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-gray-900 line-clamp-2">
                          {notification.title}
                        </p>
                        <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                          {notification.message}
                        </p>
                        <p className="text-xs text-gray-500 mt-2">
                          {formatTime(notification.timestamp)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          {notifications.length > 0 && (
            <div className="px-4 py-3 border-t border-gray-200 bg-gray-50">
              <button
                onClick={() => {
                  // In a real app, this would clear notifications
                  setIsOpen(false)
                }}
                className="text-xs font-medium text-blue-600 hover:text-blue-700 transition-colors"
              >
                View all notifications →
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default RealtimeBell
