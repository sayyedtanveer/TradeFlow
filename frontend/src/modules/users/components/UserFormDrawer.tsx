import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { usersService } from "@/services/users.service"
import { supplyChainApi } from "@/services/supply-chain.service"
import { AVAILABLE_ROLES } from "@/lib/roles.config"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { FormSkeleton } from "@/components/shared/LoadingSkeleton"
import { Save, Copy, Check } from "lucide-react"
import { Checkbox } from "@/components/ui/checkbox"
import { Drawer } from "@/components/shared/Drawer"
import { useEffect, useState } from "react"
import { useToast } from "@/hooks/use-toast"

const userSchema = z.object({
  email: z.string().email("Invalid email address"),
  first_name: z.string().min(2, "First name is required"),
  last_name: z.string().min(2, "Last name is required"),
  role: z.string().min(1, "Role is required"),
  is_active: z.boolean(),
  supplier_id: z.string().optional().nullable(),
})

type UserFormValues = z.infer<typeof userSchema>

interface Props {
  userId: string | null
  open: boolean
  onClose: () => void
}

export function UserFormDrawer({ userId, open, onClose }: Props) {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const isEditing = Boolean(userId && userId !== "new")
  
  const [tempPassword, setTempPassword] = useState<string | null>(null)
  const [copiedPassword, setCopiedPassword] = useState(false)

  const { data: user, isLoading: isFetching } = useQuery({
    queryKey: ["user", userId],
    queryFn: () => usersService.getUser(userId!),
    enabled: isEditing && open,
  })

  const { data: suppliersData } = useQuery({
    queryKey: ["suppliers"],
    queryFn: async () => {
      const res = await supplyChainApi.listSuppliers()
      return res.data || []
    },
  })

  const { register, handleSubmit, formState: { errors }, setValue, watch, reset } = useForm<UserFormValues>({
    resolver: zodResolver(userSchema),
    defaultValues: {
      email: "",
      first_name: "",
      last_name: "",
      role: "operator",
      is_active: true,
      supplier_id: null,
    }
  })

  // Reset form when user data loads or modal opens for "new"
  useEffect(() => {
    if (user) {
      reset({
        email: user.email,
        first_name: user.first_name,
        last_name: user.last_name,
        role: user.role,
        is_active: user.is_active,
        supplier_id: (user as any).supplier_id || null,
      })
    } else if (userId === "new") {
      reset({
        email: "",
        first_name: "",
        last_name: "",
        role: "operator",
        is_active: true,
        supplier_id: null,
      })
    }
  }, [user, userId, reset])

  // Reset temp password and copy state when drawer opens/closes
  useEffect(() => {
    if (!open) {
      setTempPassword(null)
      setCopiedPassword(false)
    }
  }, [open])

  const copyToClipboard = () => {
    if (tempPassword) {
      navigator.clipboard.writeText(tempPassword)
      setCopiedPassword(true)
      setTimeout(() => setCopiedPassword(false), 2000)
    }
  }

  const saveMutation = useMutation({
    mutationFn: async (data: UserFormValues) => {
      if (isEditing) {
        return usersService.updateUser(userId!, data)
      } else {
        return usersService.createUser(data)
      }
    },
    onSuccess: (response: any) => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
      
      if (!isEditing && response?.temporary_password) {
        // Show temporary password for new user
        setTempPassword(response.temporary_password)
        toast({
          title: "User Created Successfully",
          description: "Share the temporary password with the user. They will be prompted to change it on first login.",
          variant: "default",
        })
      } else {
        toast({
          title: "Success",
          description: isEditing ? "User updated successfully" : "User created successfully",
        })
        saveMutation.reset()
        onClose()
      }
    },
    onError: (error: any) => {
      const message = error?.response?.data?.detail || error?.message || "Failed to save user"
      toast({
        title: "Error",
        description: message,
        variant: "destructive",
      })
      saveMutation.reset()
    }
  })

  // Show temporary password screen
  if (tempPassword) {
    return (
      <Drawer 
        open={open} 
        onOpenChange={(v) => !v && onClose()} 
        title="User Created Successfully"
        description="Your new team member's login credentials are ready."
      >
        <div className="space-y-6 pb-8">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-3">
            <p className="text-sm text-gray-700">
              Share these credentials with the new user. They will be prompted to change their password on first login.
            </p>
            
            <div className="space-y-2">
              <Label className="text-sm font-medium">Temporary Password</Label>
              <div className="flex items-center gap-2 bg-white border border-gray-300 rounded px-3 py-2">
                <code className="flex-1 font-mono text-sm text-gray-800 break-all">{tempPassword}</code>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={copyToClipboard}
                  className="shrink-0"
                >
                  {copiedPassword ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>

            <div className="bg-yellow-50 border border-yellow-300 rounded p-3">
              <p className="text-xs text-yellow-800">
                <strong>Important:</strong> The password is only shown once. Make sure to share it with the user securely.
              </p>
            </div>
          </div>

          <div className="pt-4 flex gap-3 w-full sm:justify-end">
            <Button 
              type="button" 
              onClick={() => {
                setTempPassword(null)
                onClose()
              }}
              className="w-full sm:w-auto"
            >
              Done
            </Button>
          </div>
        </div>
      </Drawer>
    )
  }

  const onSubmit = (data: UserFormValues) => {
    saveMutation.mutate(data)
  }

  return (
    <Drawer 
      open={open} 
      onOpenChange={(v) => !v && onClose()} 
      title={isEditing ? "Edit User" : "Invite User"}
      description={isEditing ? `Update details for ${user?.email || "user"}` : "Add a new team member."}
    >
      {isEditing && isFetching ? (
        <FormSkeleton fields={4} />
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 pb-8">
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email Address</Label>
              <Input id="email" type="email" placeholder="user@acme.com" {...register("email")} disabled={isEditing} autoFocus />
              {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="first_name">First Name</Label>
                <Input id="first_name" placeholder="John" {...register("first_name")} />
                {errors.first_name && <p className="text-xs text-destructive">{errors.first_name.message}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="last_name">Last Name</Label>
                <Input id="last_name" placeholder="Doe" {...register("last_name")} />
                {errors.last_name && <p className="text-xs text-destructive">{errors.last_name.message}</p>}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <Select 
                value={watch("role")} 
                onValueChange={(val) => setValue("role", val, { shouldValidate: true })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select Role" />
                </SelectTrigger>
                <SelectContent>
                  {AVAILABLE_ROLES.map((role) => (
                    <SelectItem key={role.value} value={role.value}>
                      {role.label} ({role.description})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.role && <p className="text-xs text-destructive">{errors.role.message}</p>}
            </div>

            {watch("role") === "supplier" && (
              <div className="space-y-2 bg-blue-50 p-3 rounded border border-blue-200">
                <Label htmlFor="supplier_id">Link to Supplier (Required for Supplier Portal)</Label>
                <Select 
                  value={watch("supplier_id") || ""} 
                  onValueChange={(val) => setValue("supplier_id", val || null, { shouldValidate: true })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Supplier" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">— None —</SelectItem>
                    {suppliersData?.map((supplier: any) => (
                      <SelectItem key={supplier.id} value={supplier.id}>
                        {supplier.code} — {supplier.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-600">
                  Link this user to a supplier so they can access the supplier portal and manage purchase orders.
                </p>
              </div>
            )}

            <div className="flex items-center space-x-2 pt-2">
              <Checkbox 
                id="is_active" 
                checked={watch("is_active")} 
                onCheckedChange={(checked) => setValue("is_active", checked === true)} 
              />
              <Label htmlFor="is_active" className="text-sm font-normal cursor-pointer">
                User is active and can log in
              </Label>
            </div>
          </div>
          
          <div className="pt-4 flex gap-3 w-full sm:justify-end">
            <Button type="button" variant="outline" onClick={onClose} className="w-full sm:w-auto">Cancel</Button>
            <Button type="submit" disabled={saveMutation.isPending} className="w-full sm:w-auto">
              <Save className="mr-2 h-4 w-4" />
              {saveMutation.isPending ? "Saving..." : "Save User"}
            </Button>
          </div>
        </form>
      )}
    </Drawer>
  )
}
