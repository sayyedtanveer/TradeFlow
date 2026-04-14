import { useState, useRef, useEffect } from 'react'
import { AlertCircle, Loader2 } from 'lucide-react'

export interface TwoFactorInputProps {
  onSubmit: (code: string) => Promise<void>
  onBackupCodeMode?: () => void
  isLoading?: boolean
  error?: string | null
}

/**
 * TwoFactorInput Component
 * Input for 6-digit TOTP code during login
 */
export const TwoFactorInput = ({
  onSubmit,
  onBackupCodeMode,
  isLoading = false,
  error = null,
}: TwoFactorInputProps) => {
  const [code, setCode] = useState('')
  const [isBackupMode, setIsBackupMode] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // Auto-focus on mode change
  useEffect(() => {
    inputRef.current?.focus()
  }, [isBackupMode])

  const handleChange = (value: string) => {
    if (isBackupMode) {
      // Backup code format: XXXX-XXXX
      // Allow alphanumeric and dashes
      const cleaned = value.toUpperCase().replace(/[^A-Z0-9-]/g, '')
      setCode(cleaned)
    } else {
      // TOTP code: digits only
      const cleaned = value.replace(/\D/g, '')
      setCode(cleaned.slice(0, 6))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (isBackupMode && code.length !== 11) {
      // Format: XXXX-XXXX = 11 chars
      return
    }

    if (!isBackupMode && code.length !== 6) {
      return
    }

    try {
      await onSubmit(code)
    } catch (err) {
      // Error handled by parent
    }
  }

  const toggleMode = () => {
    setCode('')
    setIsBackupMode(!isBackupMode)
    if (!isBackupMode && onBackupCodeMode) {
      onBackupCodeMode()
    }
  }

  const isValid =
    isBackupMode ?
      code.length === 11 && code.match(/^[A-Z0-9]{4}-[A-Z0-9]{4}$/)
    : code.length === 6

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Mode Indicator */}
      <div className="rounded-lg bg-blue-50 px-4 py-2 text-center text-sm font-medium text-blue-900">
        {isBackupMode ? 'Using Backup Code' : 'Enter TOTP Code'}
      </div>

      {/* Error Message */}
      {error && (
        <div className="flex items-start gap-3 rounded-lg bg-red-50 p-3">
          <AlertCircle className="h-5 w-5 flex-shrink-0 text-red-600" />
          <div className="text-sm text-red-800">{error}</div>
        </div>
      )}

      {/* Input */}
      <div>
        <label className="block text-sm font-medium text-gray-700">
          {isBackupMode ? 'Backup Code' : 'Authentication Code'}
        </label>

        <input
          ref={inputRef}
          type="text"
          inputMode={isBackupMode ? 'text' : 'numeric'}
          value={code}
          onChange={(e) => handleChange(e.target.value)}
          placeholder={isBackupMode ? 'XXXX-XXXX' : '000000'}
          maxLength={isBackupMode ? 11 : 6}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 text-center font-mono text-2xl tracking-widest focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
        />

        {/* Helper Text */}
        <p className="mt-2 text-xs text-gray-600">
          {isBackupMode ? (
            <>Enter one of your 10 backup codes (format: XXXX-XXXX)</>
          ) : (
            <>Enter the 6-digit code from your authenticator app</>
          )}
        </p>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isLoading || !isValid}
        className="w-full rounded-lg bg-blue-600 px-4 py-3 font-medium text-white transition-colors hover:bg-blue-700 disabled:bg-gray-400"
      >
        {isLoading ? (
          <div className="flex items-center justify-center gap-2">
            <Loader2 className="h-5 w-5 animate-spin" />
            Verifying...
          </div>
        ) : (
          'Verify Code'
        )}
      </button>

      {/* Mode Toggle */}
      <button
        type="button"
        onClick={toggleMode}
        className="block w-full text-center text-sm text-blue-600 hover:text-blue-700 hover:underline"
      >
        {isBackupMode ? 'Use authenticator code instead' : 'Use backup code instead'}
      </button>

      {/* Remember Device Option */}
      <div className="flex items-center gap-3 rounded-lg bg-gray-50 p-3">
        <input
          type="checkbox"
          id="remember-device"
          className="h-4 w-4 rounded border-gray-300 text-blue-600"
        />
        <label htmlFor="remember-device" className="text-sm text-gray-700">
          Trust this device for 30 days
        </label>
      </div>

      {/* Recovery Link */}
      <button
        type="button"
        className="block w-full text-center text-xs text-gray-600 hover:text-gray-800"
      >
        Lost access to your authenticator app?
      </button>
    </form>
  )
}

export default TwoFactorInput
