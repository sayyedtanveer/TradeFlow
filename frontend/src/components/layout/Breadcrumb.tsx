import { Link, useLocation } from "react-router-dom"
import { ChevronRight, Home } from "lucide-react"

export function Breadcrumb() {
  const location = useLocation()
  
  // Don't show breadcrumbs on dashboard root
  if (location.pathname === "/") {
    return null
  }

  // Very basic breadcrumb, e.g. /inventory/products -> Inventory > Products
  const paths = location.pathname.split("/").filter(Boolean)

  return (
    <nav aria-label="Breadcrumb" className="mb-4 flex items-center text-sm text-muted-foreground">
      <Link to="/" className="flex items-center hover:text-foreground transition-colors">
        <Home className="h-4 w-4" />
        <span className="sr-only">Home</span>
      </Link>
      
      {paths.map((path, index) => {
        const isLast = index === paths.length - 1
        const to = `/${paths.slice(0, index + 1).join("/")}`
        
        // Format path segment: capitalize first letter, replace hyphens
        const title = path.charAt(0).toUpperCase() + path.slice(1).replace(/-/g, " ")

        return (
          <div key={path} className="flex items-center">
            <ChevronRight className="h-4 w-4 mx-1" />
            {isLast ? (
              <span className="text-foreground font-medium" aria-current="page">
                {title}
              </span>
            ) : (
              <Link to={to} className="hover:text-foreground transition-colors">
                {title}
              </Link>
            )}
          </div>
        )
      })}
    </nav>
  )
}
