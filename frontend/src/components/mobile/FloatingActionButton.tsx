import { LucideIcon } from 'lucide-react'

export interface FloatingActionButtonProps {
  icon: LucideIcon
  label?: string
  onClick: () => void
  className?: string
  variant?: 'primary' | 'secondary'
  size?: 'small' | 'medium' | 'large'
}

/**
 * FloatingActionButton Component
 * Floating action button for primary mobile actions
 */
export const FloatingActionButton = ({
  icon: Icon,
  label,
  onClick,
  className = '',
  variant = 'primary',
  size = 'large',
}: FloatingActionButtonProps) => {
  const sizeClasses = {
    small: 'h-12 w-12',
    medium: 'h-14 w-14',
    large: 'h-16 w-16',
  }

  const sizeIconClasses = {
    small: 'h-6 w-6',
    medium: 'h-7 w-7',
    large: 'h-8 w-8',
  }

  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 shadow-lg hover:shadow-xl',
    secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 active:bg-gray-400 shadow-md hover:shadow-lg',
  }

  const computedSize = sizeClasses[size]
  const computedIconSize = sizeIconClasses[size]
  const computedVariant = variantClasses[variant]

  return (
    <button
      onClick={onClick}
      className={`
        fixed right-4 flex items-center justify-center gap-2 rounded-full
        font-medium transition-all active:scale-95
        ${computedSize} ${computedVariant} ${className}
      `}
      style={{
        bottom: 'calc(80px + 16px)',
        zIndex: 39, // Below OfflineIndicator, above other content
      }}
      title={label}
    >
      <Icon className={computedIconSize} />
      {label && <span className="text-sm">{label}</span>}
    </button>
  )
}

export default FloatingActionButton
