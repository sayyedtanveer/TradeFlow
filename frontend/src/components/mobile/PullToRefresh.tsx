import { useEffect, useRef, useState } from 'react'
import { ChevronDown, Loader2 } from 'lucide-react'

export interface PullToRefreshProps {
  onRefresh: () => Promise<void>
  children: React.ReactNode
  className?: string
  threshold?: number // pixels to pull before refresh threshold
}

/**
 * PullToRefresh Component
 * Allows users to pull down on mobile to trigger refresh
 */
export const PullToRefresh = ({
  onRefresh,
  children,
  className = '',
  threshold = 80,
}: PullToRefreshProps) => {
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [pullDistance, setPullDistance] = useState(0)
  const startYRef = useRef(0)
  const scrollStartRef = useRef(0)
  const refreshTimeoutRef = useRef<ReturnType<typeof setTimeout>>()

  useEffect(() => {
    const container = document.querySelector('[data-pull-to-refresh="true"]')
    if (!container) return

    const handleTouchStart = (e: TouchEvent) => {
      startYRef.current = e.touches[0].clientY
      scrollStartRef.current = container.scrollTop
    }

    const handleTouchMove = (e: TouchEvent) => {
      // Only allow pull-to-refresh when at top of scroll
      if (container.scrollTop > 0) {
        setPullDistance(0)
        return
      }

      const currentY = e.touches[0].clientY
      const distance = currentY - startYRef.current

      if (distance > 0 && !isRefreshing) {
        e.preventDefault()
        setPullDistance(distance)
      }
    }

    const handleTouchEnd = async () => {
      if (pullDistance >= threshold && !isRefreshing) {
        setIsRefreshing(true)
        try {
          await onRefresh()
        } catch (err) {
          console.error('Refresh error:', err)
        } finally {
          setIsRefreshing(false)
          setPullDistance(0)

          // Animate back to top
          if (refreshTimeoutRef.current) {
            clearTimeout(refreshTimeoutRef.current)
          }
        }
      } else {
        // Animate back to start
        setPullDistance(0)
      }
    }

    container.addEventListener('touchstart' as any, handleTouchStart)
    container.addEventListener('touchmove' as any, handleTouchMove, { passive: false })
    container.addEventListener('touchend' as any, handleTouchEnd)

    return () => {
      container.removeEventListener('touchstart' as any, handleTouchStart)
      container.removeEventListener('touchmove' as any, handleTouchMove)
      container.removeEventListener('touchend' as any, handleTouchEnd)
    }
  }, [pullDistance, threshold, isRefreshing, onRefresh])

  const pulledEnough = pullDistance >= threshold
  const rotationDegrees = Math.min(pullDistance / 2, 180)

  return (
    <div
      data-pull-to-refresh="true"
      className={`relative overflow-y-auto ${className}`}
      style={{
        WebkitOverscrollBehavior: 'contain',
      } as any}
    >
      {/* Pull-to-refresh header */}
      <div
        className={`absolute inset-x-0 -top-20 flex items-center justify-center transition-transform duration-300 ${
          pullDistance > 0 ? 'translate-y-0' : ''
        }`}
        style={{
          transform: `translateY(${Math.max(0, pullDistance - 80)}px)`,
        }}
      >
        <div className="flex flex-col items-center gap-2 rounded-full bg-white p-4 shadow-lg">
          {isRefreshing ? (
            <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
          ) : (
            <ChevronDown
              className={`h-6 w-6 transition-transform ${
                pulledEnough ? 'text-blue-600' : 'text-gray-400'
              }`}
              style={{
                transform: `rotate(${rotationDegrees}deg)`,
              }}
            />
          )}
          <p className="text-xs font-medium text-gray-600">
            {isRefreshing ? 'Refreshing...' : pulledEnough ? 'Release to refresh' : 'Pull to refresh'}
          </p>
        </div>
      </div>

      {/* Content */}
      <div
        style={{
          transform: `translateY(${pullDistance}px)`,
          transition: isRefreshing || pullDistance === 0 ? 'transform 0.3s ease-out' : 'none',
        }}
      >
        {children}
      </div>
    </div>
  )
}

export default PullToRefresh
