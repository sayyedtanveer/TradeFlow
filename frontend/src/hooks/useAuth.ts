import { useMutation } from "@tanstack/react-query"
import { authService } from "@/services/auth.service"
import { useAuthStore } from "@/app/store/authStore"
import { useTenantStore } from "@/app/store/tenantStore"
import { useNavigate } from "react-router-dom"
import { useToast } from "@/hooks/use-toast"

export function useAuth() {
  const { setAuth, setUser, logout: clearAuthStore, isAuthenticated, user, tenant_id } = useAuthStore()
  const { clearTenant, setTenantInfo } = useTenantStore()
  const navigate = useNavigate()
  const { toast } = useToast()

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
        setTenantInfo(meResult.tenant.name, meResult.tenant.slug, meResult.tenant.plan)
        
        toast({ title: "Welcome back!" })
        
        // 3. Redirect to dashboard
        navigate("/", { replace: true })
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
  }
}
