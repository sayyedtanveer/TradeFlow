import { Link, useLocation } from 'react-router-dom'
import {
  Home,
  Package,
  Wrench,
  BarChart3,
  Settings,
  LucideIcon,
} from 'lucide-react'

export interface NavItem {
  label: string
  path: string
  icon: LucideIcon
}

const DEFAULT_NAV_ITEMS: NavItem[] = [
  {
    label: 'Dashboard',
    path: '/dashboard',
    icon: Home,
  },
  {
    label: 'Inventory',
    path: '/inventory',
    icon: Package,
  },
  {
    label: 'Work Orders',
    path: '/work-orders',
    icon: Wrench,
  },
  {
    label: 'Reports',
    path: '/reports',
    icon: BarChart3,
  },
  {
    label: 'Settings',
    path: '/settings',
    icon: Settings,
  },
]

export interface BottomNavigationProps {
  items?: NavItem[]
  className?: string
}

/**
 * BottomNavigation Component
 * Mobile-first tab navigation at bottom of screen
 */
export const BottomNavigation = ({
  items = DEFAULT_NAV_ITEMS,
  className = '',
}: BottomNavigationProps) => {
  const location = useLocation()

  const isActive = (path: string) => {
    if (path === '/dashboard') {
      return location.pathname === '/' || location.pathname === '/dashboard'
    }
    return location.pathname.startsWith(path)
  }

  return (
    <nav
      className={`fixed bottom-0 left-0 right-0 border-t border-gray-200 bg-white ${className}`}
      // Don't display on desktop - handled by media query in CSS
      style={{ display: 'none' }}
      data-mobile-nav="true"
    >
      <style>{`
        @media (max-width: 768px) {
          nav[data-mobile-nav="true"] {
            display: block !important;
          }
          
          body {
            padding-bottom: 80px;
          }
        }
      `}</style>

      <div className="flex items-center justify-around">
        {items.map((item) => {
          const Icon = item.icon
          const active = isActive(item.path)

          return (
            <Link
              key={item.path}
              to={item.path}
              className={`
                flex flex-1 flex-col items-center justify-center gap-1 px-3 py-3 text-xs font-medium transition-colors
                ${
                  active
                    ? 'border-t-2 border-blue-600 text-blue-600'
                    : 'border-t-2 border-transparent text-gray-600 hover:text-gray-900'
                }
              `}
            >
              <Icon className="h-6 w-6" />
              <span className="hidden sm:inline">{item.label}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}

export default BottomNavigation
