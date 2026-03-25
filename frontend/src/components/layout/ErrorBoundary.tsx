/**
 * Error Boundary Component
 * 
 * Catches React rendering errors and displays them in a user-friendly way
 * instead of crashing the entire application.
 */

import { ReactNode, Component, ErrorInfo } from "react"
import { AlertTriangle, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"

interface Props {
  children: ReactNode
  fallback?: (error: Error, reset: () => void) => ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error details for debugging
    console.error("Error caught by ErrorBoundary:", error, errorInfo)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
    // Optional: reload the page to fully reset state
    // window.location.reload()
  }

  render() {
    if (this.state.hasError && this.state.error) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.handleReset)
      }

      // Default error UI
      return (
        <div className="flex items-center justify-center min-h-[400px] p-4 bg-background">
          <Card className="w-full max-w-md border-destructive/50 bg-destructive/10">
            <CardHeader>
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-destructive" />
                <CardTitle>Something went wrong</CardTitle>
              </div>
              <CardDescription>
                An error occurrred while rendering this page
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="bg-background p-3 rounded-md text-sm font-mono text-muted-foreground max-h-[200px] overflow-y-auto break-words">
                {this.state.error.message}
              </div>
              <p className="text-xs text-muted-foreground">
                If this error persists, please refresh the page or contact support.
              </p>
            </CardContent>
            <CardFooter className="gap-2">
              <Button variant="outline" onClick={this.handleReset} className="flex-1">
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
              <Button
                variant="outline"
                onClick={() => (window.location.href = "/")}
                className="flex-1"
              >
                Go Home
              </Button>
            </CardFooter>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}
