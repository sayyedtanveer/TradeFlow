import { useState, useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { PackageSearch, Plus, Search, AlertCircle } from "lucide-react"
import { productService } from "@/services/product.service"
import { usePermissions } from "@/hooks/usePermissions"
import { useToast } from "@/hooks/use-toast"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"

export default function ProductTemplateListPage() {
  const navigate = useNavigate()
  const { hasRole } = usePermissions()
  const { toast } = useToast()
  const canEdit = hasRole(["ADMIN", "MANAGER"])
  
  const [query, setQuery] = useState("")
  const [debouncedQuery, setDebouncedQuery] = useState("")
  const [page, setPage] = useState(1)

  // simple debounce
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(query)
      setPage(1)
    }, 400)
    return () => clearTimeout(handler)
  }, [query])

  const { data, isLoading, error, isError } = useQuery({
    queryKey: ["products", "templates", debouncedQuery, page],
    queryFn: () => productService.getTemplates({ query: debouncedQuery, page, page_size: 20 }),
    staleTime: 10_000,
  })

  // Show error toast if query fails
  useEffect(() => {
    if (isError && error && !isLoading) {
      toast({
        title: "Error loading templates",
        description: error instanceof Error ? error.message : "Failed to load product templates. Please try again.",
        variant: "destructive",
      })
    }
  }, [isError, error, isLoading, toast])

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Product Templates</h1>
          <p className="text-muted-foreground">Manage multi-variant product definitions.</p>
        </div>
        {canEdit && (
          <Button onClick={() => navigate("/products/new")}>
            <Plus className="w-4 h-4 mr-2" />
            New Template
          </Button>
        )}
      </div>

      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-muted-foreground" />
          <Input 
            placeholder="Search by code or name..." 
            className="pl-8" 
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="rounded-md border bg-card">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/50">
            <tr>
              <th className="h-10 px-4 text-left font-medium text-muted-foreground">Code</th>
              <th className="h-10 px-4 text-left font-medium text-muted-foreground">Name</th>
              <th className="h-10 px-4 text-left font-medium text-muted-foreground">Category</th>
              <th className="h-10 px-4 text-left font-medium text-muted-foreground">Status</th>
              <th className="h-10 px-4 text-right font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {isError ? (
              <tr>
                <td colSpan={5} className="py-10 px-4">
                  <div className="flex items-start gap-3 max-w-md bg-destructive/10 border border-destructive/50 rounded-md p-4 mx-auto">
                    <AlertCircle className="h-5 w-5 text-destructive mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="font-medium text-destructive">Failed to load templates</p>
                      <p className="text-sm text-destructive/80 mt-1">
                        {error instanceof Error ? error.message : "An error occurred while loading product templates."}
                      </p>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={() => window.location.reload()}
                        className="mt-3"
                      >
                        Retry
                      </Button>
                    </div>
                  </div>
                </td>
              </tr>
            ) : isLoading ? (
              <tr>
                <td colSpan={5} className="py-10 text-center text-muted-foreground">
                  Loading templates...
                </td>
              </tr>
            ) : data?.items.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-12 text-center text-muted-foreground">
                  <PackageSearch className="w-8 h-8 mx-auto mb-3 opacity-50" />
                  <p>No product templates found.</p>
                </td>
              </tr>
            ) : (
              data?.items.map((tpl) => (
                <tr key={tpl.id} className="hover:bg-muted/30">
                  <td className="px-4 py-3 font-mono">{tpl.code}</td>
                  <td className="px-4 py-3 font-medium">{tpl.name}</td>
                  <td className="px-4 py-3 text-muted-foreground">{tpl.category_id ? "—" : "—"}</td>
                  <td className="px-4 py-3">
                    <Badge variant={tpl.is_active ? "outline" : "secondary"}>
                      {tpl.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button variant="ghost" size="sm" onClick={() => navigate(`/products/${tpl.id}/edit`)}>
                      {canEdit ? "Edit" : "View"}
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {data && data.total > data.page_size && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {(page - 1) * data.page_size + 1}–{Math.min(page * data.page_size, data.total)} of {data.total}
          </p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={page * data.page_size >= data.total} onClick={() => setPage((p) => p + 1)}>
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
