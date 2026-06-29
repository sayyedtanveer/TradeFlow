import { useMutation, useQueryClient } from "@tanstack/react-query"
import { authService } from "@/services/auth.service"
import { useAuthStore } from "@/app/store/authStore"
import { getPostLoginPath } from "@/lib/roles.config"
import { useTenantStore } from "@/app/store/tenantStore"
import { useNavigate } from "react-router-dom"
import { useToast } from "@/hooks/use-toast"

export function useAuth() {
  const {
    setAuth,
    setUser,
    setPermissions,
    setSupplierAndClient,
    logout: clearAuthStore,
    isAuthenticated,
    user,
    tenant_id,
  } = useAuthStore()
  const { clearTenant, setTenantInfo } = useTenantStore()
  const navigate = useNavigate()
  const { toast } = useToast()
  const queryClient = useQueryClient()

  // Mutation for login
  const loginMutation = useMutation({
    mutationFn: authService.login,
    onSuccess: async (data) => {
      // 1. Store token
      setAuth(data.access_token, data.tenant_id)
      
      // 2. Fetch current user profile + tenant info with the new token
      try {
        const meResult = await authService.getMe()
        setUser(meResult.user)
        setPermissions(meResult.permissions ?? [])
        setSupplierAndClient(meResult.user.supplier_id ?? null, meResult.user.client_id ?? null)
        setTenantInfo(meResult.tenant.name, meResult.tenant.slug, meResult.tenant.plan)

        // Ensure role-based UI modules are refreshed now that user role is known
        try {
          await queryClient.invalidateQueries({ queryKey: ["system-map"] })
        } catch (e) {
          // ignore – best-effort refresh
        }

        toast({ title: "Welcome back!" })

        const home = getPostLoginPath(meResult.user.role)
        navigate(home, { replace: true })
      } catch (err) {
        clearAuthStore()
        toast({ title: "Failed to fetch profile", variant: "destructive" })
      }
    },
    onError: (error: any) => {
      toast({
        title: "Login failed",
        description: error.response?.data?.detail || "Invalid email or password.",
        variant: "destructive",
      })
    },
  })

  // Mutation for registration
  const registerMutation = useMutation({
    mutationFn: authService.registerTenant,
    onSuccess: async (data) => {
      setAuth(data.access_token, data.tenant_id)
      try {
        const meResult = await authService.getMe()
        setUser(meResult.user)
        setPermissions(meResult.permissions ?? [])
        setSupplierAndClient(meResult.user.supplier_id ?? null, meResult.user.client_id ?? null)
        setTenantInfo(meResult.tenant.name, meResult.tenant.slug, meResult.tenant.plan)
        
        toast({ title: "Tenant created successfully! Welcome." })
        navigate("/", { replace: true })
      } catch (err) {
        clearAuthStore()
        navigate("/login")
      }
    },
    onError: (error: any) => {
      toast({
        title: "Registration failed",
        description: error.response?.data?.detail || "An error occurred during registration.",
        variant: "destructive",
      })
    },
  })

  const logout = () => {
    clearAuthStore()
    clearTenant()
    // Optional: call backend to invalidate token if implemented
    navigate("/login", { replace: true })
  }

  return {
    login: loginMutation.mutate,
    isLoggingIn: loginMutation.isPending,
    register: registerMutation.mutate,
    isRegistering: registerMutation.isPending,
    logout,
    isAuthenticated,
    user,
    tenant_id,
    supplier_id: useAuthStore((s) => s.supplier_id),
    client_id: useAuthStore((s) => s.client_id),
  }
}
