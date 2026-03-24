import { Button } from "@/components/ui/button"
import { useNavigate } from "react-router-dom"
import { ShieldAlert, FileQuestion } from "lucide-react"

export function NotFoundPage() {
  const navigate = useNavigate()
  return (
    <div className="flex h-screen w-full flex-col items-center justify-center space-y-4 bg-background px-4 text-center">
      <div className="rounded-full bg-muted p-6">
        <FileQuestion className="h-12 w-12 text-muted-foreground" />
      </div>
      <h1 className="text-4xl font-bold tracking-tight">404</h1>
      <h2 className="text-xl font-medium">Page Not Found</h2>
      <p className="max-w-md text-muted-foreground">
        The page you are looking for doesn't exist or has been moved.
      </p>
      <Button onClick={() => navigate("/")} className="mt-6">
        Return to Dashboard
      </Button>
    </div>
  )
}

export function ForbiddenPage() {
  const navigate = useNavigate()
  return (
    <div className="flex h-screen w-full flex-col items-center justify-center space-y-4 bg-background px-4 text-center">
      <div className="rounded-full bg-destructive/10 p-6">
        <ShieldAlert className="h-12 w-12 text-destructive" />
      </div>
      <h1 className="text-4xl font-bold tracking-tight">403</h1>
      <h2 className="text-xl font-medium">Access Denied</h2>
      <p className="max-w-md text-muted-foreground">
        You don't have permission to view this page. Please contact your administrator if you believe this is a mistake.
      </p>
      <Button onClick={() => navigate("/")} className="mt-6">
        Return to Dashboard
      </Button>
    </div>
  )
}
