import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface ForgotPasswordModalProps {
  isOpen: boolean
  onClose: () => void
}

type Step = "request" | "reset" | "success"

export default function ForgotPasswordModal({ isOpen, onClose }: ForgotPasswordModalProps) {
  const [step, setStep] = useState<Step>("request")
  const [email, setEmail] = useState("")
  const [resetToken, setResetToken] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")

  // Request password reset
  const requestMutation = useMutation({
    mutationFn: async (email: string) => {
      const response = await fetch("/api/v1/forgot-password/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      })
      if (!response.ok) {
        throw new Error("Failed to request password reset")
      }
      return response.json()
    },
    onSuccess: (data) => {
      setMessage("Check your email for password reset instructions")
      if (data.reset_token) {
        // Development mode - token is provided
        setResetToken(data.reset_token)
        setStep("reset")
      } else {
        // Production mode - token sent via email
        setTimeout(() => {
          handleClose()
        }, 2000)
      }
    },
    onError: (error: any) => {
      setError(error.message || "Failed to request password reset")
    },
  })

  // Reset password
  const resetMutation = useMutation({
    mutationFn: async () => {
      if (newPassword !== confirmPassword) {
        throw new Error("Passwords do not match")
      }
      if (newPassword.length < 8) {
        throw new Error("Password must be at least 8 characters")
      }

      const response = await fetch("/api/v1/forgot-password/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: resetToken,
          new_password: newPassword,
        }),
      })
      if (!response.ok) {
        throw new Error("Failed to reset password")
      }
      return response.json()
    },
    onSuccess: (data) => {
      setMessage(data.message || "Password reset successful!")
      setStep("success")
      setTimeout(() => {
        handleClose()
      }, 2000)
    },
    onError: (error: any) => {
      setError(error.message || "Failed to reset password")
    },
  })

  const handleClose = () => {
    setStep("request")
    setEmail("")
    setResetToken("")
    setNewPassword("")
    setConfirmPassword("")
    setMessage("")
    setError("")
    onClose()
  }

  const handleRequestSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    if (!email) {
      setError("Please enter your email")
      return
    }
    requestMutation.mutate(email)
  }

  const handleResetSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    resetMutation.mutate()
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[400px]">
        {step === "request" && (
          <>
            <DialogHeader>
              <DialogTitle>Reset Your Password</DialogTitle>
              <DialogDescription>
                Enter your email address and we'll send you a password reset link
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleRequestSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="reset-email">Email Address</Label>
                <Input
                  id="reset-email"
                  type="email"
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={requestMutation.isPending}
                  autoFocus
                />
              </div>

              {error && <div className="rounded bg-red-50 p-3 text-sm text-red-600">{error}</div>}

              {message && <div className="rounded bg-green-50 p-3 text-sm text-green-600">{message}</div>}

              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={handleClose} className="flex-1">
                  Cancel
                </Button>
                <Button
                  type="submit"
                  className="flex-1"
                  disabled={requestMutation.isPending}
                >
                  {requestMutation.isPending ? "Sending..." : "Send Reset Link"}
                </Button>
              </div>
            </form>
          </>
        )}

        {step === "reset" && (
          <>
            <DialogHeader>
              <DialogTitle>Enter New Password</DialogTitle>
              <DialogDescription>
                Create a new password for your account
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleResetSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="new-password">New Password</Label>
                <Input
                  id="new-password"
                  type="password"
                  placeholder="At least 8 characters"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  disabled={resetMutation.isPending}
                  autoFocus
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirm-password">Confirm Password</Label>
                <Input
                  id="confirm-password"
                  type="password"
                  placeholder="Confirm your password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={resetMutation.isPending}
                />
              </div>

              {error && <div className="rounded bg-red-50 p-3 text-sm text-red-600">{error}</div>}

              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={handleClose} className="flex-1">
                  Cancel
                </Button>
                <Button
                  type="submit"
                  className="flex-1"
                  disabled={resetMutation.isPending}
                >
                  {resetMutation.isPending ? "Resetting..." : "Reset Password"}
                </Button>
              </div>
            </form>
          </>
        )}

        {step === "success" && (
          <>
            <DialogHeader>
              <DialogTitle>Success!</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 text-center">
              <p className="text-sm text-gray-600">{message}</p>
              <p className="text-xs text-gray-500">You can now log in with your new password</p>
              <Button onClick={handleClose} className="w-full">
                Close
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
