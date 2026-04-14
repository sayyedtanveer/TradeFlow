import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2, AlertCircle, Copy, Check, ChevronLeft } from 'lucide-react'
import QRCode from 'qrcode'

interface TwoFactorSetupProps {
  onComplete?: () => void
  onBack?: () => void
}

/**
 * TwoFactorSetupPage
 * Step-by-step 2FA setup wizard
 */
export const TwoFactorSetup = ({ onComplete, onBack }: TwoFactorSetupProps) => {
  const navigate = useNavigate()
  const [step, setStep] = useState<'intro' | 'scan' | 'verify' | 'backup'>('intro')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [qrCodeUrl, setQrCodeUrl] = useState<string | null>(null)
  const [secret, setSecret] = useState<string | null>(null)
  const [backupCodes, setBackupCodes] = useState<string[]>([])
  const [verificationCode, setVerificationCode] = useState('')
  const [copiedCode, setCopiedCode] = useState<string | null>(null)

  const handleEnable = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/v1/auth/2fa/enable', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
      })

      if (!response.ok) {
        throw new Error('Failed to enable 2FA')
      }

      const data = await response.json()
      setSecret(data.totp_secret)
      setQrCodeUrl(`data:image/png;base64,${data.qr_code_base64}`)
      setBackupCodes(data.backup_codes)
      setStep('scan')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const handleVerify = async () => {
    if (verificationCode.length !== 6 || !/^\d+$/.test(verificationCode)) {
      setError('Please enter a valid 6-digit code')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/v1/auth/2fa/verify-setup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({ code: verificationCode }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Code verification failed')
      }

      setStep('backup')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Verification failed')
    } finally {
      setLoading(false)
    }
  }

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code)
    setCopiedCode(code)
    setTimeout(() => setCopiedCode(null), 2000)
  }

  const handleComplete = () => {
    if (onComplete) {
      onComplete()
    } else {
      navigate('/settings/security')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="mx-auto max-w-2xl">
        {/* Header */}
        <div className="mb-8 flex items-center gap-4">
          {step !== 'intro' && (
            <button
              onClick={() => setStep(step === 'verify' ? 'scan' : step === 'backup' ? 'verify' : 'intro')}
              className="rounded-lg p-2 hover:bg-white/50"
            >
              <ChevronLeft className="h-6 w-6" />
            </button>
          )}
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Set Up Two-Factor Authentication</h1>
            <p className="text-gray-600">Secure your account with an extra layer of protection</p>
          </div>
        </div>

        {/* Step Indicator */}
        <div className="mb-8 flex gap-4">
          {['intro', 'scan', 'verify', 'backup'].map((s) => (
            <div
              key={s}
              className={`flex-1 rounded-lg px-4 py-3 text-center font-medium transition-colors ${
                s === step ? 'bg-blue-600 text-white' : 'bg-white text-gray-600'
              }`}
            >
              {s === 'intro' ? '1. Intro' : s === 'scan' ? '2. Scan' : s === 'verify' ? '3. Verify' : '4. Backup'}
            </div>
          ))}
        </div>

        {/* Content */}
        <div className="rounded-lg bg-white p-8 shadow-lg">
          {error && (
            <div className="mb-6 flex items-start gap-3 rounded-lg bg-red-50 p-4">
              <AlertCircle className="h-5 w-5 flex-shrink-0 text-red-600" />
              <div>
                <h3 className="font-medium text-red-900">Error</h3>
                <p className="text-sm text-red-800">{error}</p>
              </div>
            </div>
          )}

          {/* Step: Intro */}
          {step === 'intro' && (
            <div className="space-y-6">
              <div>
                <h2 className="mb-4 text-2xl font-semibold text-gray-900">Enhance Your Security</h2>
                <p className="text-gray-600">
                  Two-factor authentication (2FA) adds an extra layer of security to your MedTrack account. Even if someone
                  obtains your password, they cannot access your account without your authenticator code.
                </p>
              </div>

              <div className="space-y-4">
                <h3 className="font-semibold text-gray-900">What you'll need:</h3>
                <ul className="space-y-2 text-gray-600">
                  <li className="flex items-center gap-3">
                    <div className="h-2 w-2 rounded-full bg-blue-600"></div>
                    An authenticator app (Google Authenticator, Authy, Microsoft Authenticator)
                  </li>
                  <li className="flex items-center gap-3">
                    <div className="h-2 w-2 rounded-full bg-blue-600"></div>
                    Your mobile phone or tablet
                  </li>
                  <li className="flex items-center gap-3">
                    <div className="h-2 w-2 rounded-full bg-blue-600"></div>
                    A few minutes to complete setup
                  </li>
                </ul>
              </div>

              <button
                onClick={handleEnable}
                disabled={loading}
                className="w-full rounded-lg bg-blue-600 px-6 py-3 font-medium text-white transition-colors hover:bg-blue-700 disabled:bg-gray-400"
              >
                {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : 'Get Started'}
              </button>
            </div>
          )}

          {/* Step: Scan QR Code */}
          {step === 'scan' && (
            <div className="space-y-6">
              <div>
                <h2 className="mb-2 text-2xl font-semibold text-gray-900">Scan QR Code</h2>
                <p className="text-gray-600">
                  Open your authenticator app and scan this QR code, or enter the secret key manually.
                </p>
              </div>

              {/* QR Code */}
              <div className="flex justify-center rounded-lg bg-gray-50 p-6">
                {qrCodeUrl ? (
                  <img src={qrCodeUrl} alt="2FA QR Code" className="h-48 w-48" />
                ) : (
                  <div className="h-48 w-48 animate-pulse bg-gray-200"></div>
                )}
              </div>

              {/* Manual Entry */}
              <div>
                <label className="block text-sm font-medium text-gray-700">Can't scan?</label>
                <div className="mt-2 rounded-lg border border-gray-200 bg-gray-50 p-4">
                  <p className="text-xs text-gray-600">Enter this code manually in your authenticator app:</p>
                  <p className="mt-2 font-mono text-lg font-semibold text-gray-900">{secret}</p>
                </div>
              </div>

              <button
                onClick={() => setStep('verify')}
                className="w-full rounded-lg bg-blue-600 px-6 py-3 font-medium text-white transition-colors hover:bg-blue-700"
              >
                I've Scanned the Code
              </button>
            </div>
          )}

          {/* Step: Verify Code */}
          {step === 'verify' && (
            <div className="space-y-6">
              <div>
                <h2 className="mb-2 text-2xl font-semibold text-gray-900">Verify Code</h2>
                <p className="text-gray-600">Enter the 6-digit code from your authenticator app to confirm setup.</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Enter 6-digit code</label>
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, ''))}
                  placeholder="000000"
                  className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 text-center text-2xl font-mono tracking-widest focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                />
              </div>

              <button
                onClick={handleVerify}
                disabled={loading || verificationCode.length !== 6}
                className="w-full rounded-lg bg-blue-600 px-6 py-3 font-medium text-white transition-colors hover:bg-blue-700 disabled:bg-gray-400"
              >
                {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : 'Verify & Continue'}
              </button>
            </div>
          )}

          {/* Step: Backup Codes */}
          {step === 'backup' && (
            <div className="space-y-6">
              <div>
                <h2 className="mb-2 text-2xl font-semibold text-gray-900">Save Backup Codes</h2>
                <p className="text-gray-600">
                  Save these codes in a safe place. You can use them to access your account if you lose your authenticator device.
                </p>
              </div>

              {/* Backup Codes */}
              <div className="space-y-2 rounded-lg bg-gray-50 p-4">
                {backupCodes.map((code) => (
                  <div
                    key={code}
                    className="flex items-center justify-between rounded border border-gray-200 bg-white px-4 py-2"
                  >
                    <code className="font-mono text-sm font-medium text-gray-900">{code}</code>
                    <button
                      onClick={() => handleCopyCode(code)}
                      className="ml-2 rounded p-1 hover:bg-gray-100"
                    >
                      {copiedCode === code ? (
                        <Check className="h-4 w-4 text-green-600" />
                      ) : (
                        <Copy className="h-4 w-4 text-gray-400" />
                      )}
                    </button>
                  </div>
                ))}
              </div>

              {/* Download / Print */}
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    const text = backupCodes.join('\n')
                    const blob = new Blob([text], { type: 'text/plain' })
                    const url = URL.createObjectURL(blob)
                    const a = document.createElement('a')
                    a.href = url
                    a.download = '2fa-backup-codes.txt'
                    a.click()
                  }}
                  className="flex-1 rounded-lg border border-gray-300 px-4 py-2 font-medium text-gray-700 transition-colors hover:bg-gray-50"
                >
                  Download
                </button>
                <button
                  onClick={() => window.print()}
                  className="flex-1 rounded-lg border border-gray-300 px-4 py-2 font-medium text-gray-700 transition-colors hover:bg-gray-50"
                >
                  Print
                </button>
              </div>

              {/* Confirmation */}
              <div className="rounded-lg border-l-4 border-yellow-600 bg-yellow-50 p-4">
                <p className="text-sm font-medium text-yellow-800">
                  ✓ I have saved my backup codes in a safe place
                </p>
              </div>

              <button
                onClick={handleComplete}
                className="w-full rounded-lg bg-green-600 px-6 py-3 font-medium text-white transition-colors hover:bg-green-700"
              >
                Complete Setup
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default TwoFactorSetup
