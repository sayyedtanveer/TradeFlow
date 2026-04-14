import { ReactNode, useState } from 'react'
import { X, Menu } from 'lucide-react'

export interface ResponsiveSidebarProps {
  children: ReactNode
  header?: ReactNode
  footer?: ReactNode
  className?: string
  collapsed?: boolean
}

/**
 * ResponsiveSidebar Component
 * Sidebar that adapts to mobile (drawer) and desktop (sidebar)
 */
export const ResponsiveSidebar = ({
  children,
  header,
  footer,
  className = '',
  collapsed = false,
}: ResponsiveSidebarProps) => {
  const [isOpen, setIsOpen] = useState(!collapsed)

  const handleToggle = () => {
    setIsOpen(!isOpen)
  }

  const handleClose = () => {
    setIsOpen(false)
  }

  return (
    <>
      {/* Mobile Menu Button */}
      <button
        onClick={handleToggle}
        className="fixed left-0 top-0 z-50 m-4 rounded-lg bg-white p-2 shadow-md md:hidden"
      >
        <Menu className="h-6 w-6 text-gray-900" />
      </button>

      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black bg-opacity-50 md:hidden"
          onClick={handleClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed bottom-0 left-0 top-0 z-40 w-64 transform bg-white shadow-lg transition-transform duration-300 ease-in-out
          md:relative md:z-0 md:translate-x-0 md:shadow-none
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
          ${className}
        `}
      >
        <div className="flex flex-col overflow-hidden rounded-lg h-full">
          {/* Close Button (Mobile) */}
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-4 md:hidden">
            {header && <div>{header}</div>}
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-600 md:hidden"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          {/* Header (Desktop) */}
          {header && (
            <div className="hidden border-b border-gray-100 px-4 py-4 md:block">
              {header}
            </div>
          )}

          {/* Content */}
          <div className="flex-1 overflow-y-auto px-4 py-4">
            {children}
          </div>

          {/* Footer */}
          {footer && (
            <div className="border-t border-gray-100 px-4 py-4">
              {footer}
            </div>
          )}
        </div>
      </aside>
    </>
  )
}

export default ResponsiveSidebar
