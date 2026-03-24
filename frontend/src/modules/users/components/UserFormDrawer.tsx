import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { usersService } from "@/services/users.service"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { FormSkeleton } from "@/components/shared/LoadingSkeleton"
import { Save } from "lucide-react"
import { Checkbox } from "@/components/ui/checkbox"
import { Drawer } from "@/components/shared/Drawer"
import { useEffect } from "react"

const userSchema = z.object({
  email: z.string().email("Invalid email address"),
  first_name: z.string().min(2, "First name is required"),
  last_name: z.string().min(2, "Last name is required"),
  role: z.string().min(1, "Role is required"),
  is_active: z.boolean(),
})

type UserFormValues = z.infer<typeof userSchema>

interface Props {
  userId: string | null
  open: boolean
  onClose: () => void
}

export function UserFormDrawer({ userId, open, onClose }: Props) {
  const queryClient = useQueryClient()
  const isEditing = Boolean(userId && userId !== "new")

  const { data: user, isLoading: isFetching } = useQuery({
    queryKey: ["user", userId],
    queryFn: () => usersService.getUser(userId!),
    enabled: isEditing && open,
  })

  const { register, handleSubmit, formState: { errors }, setValue, watch, reset } = useForm<UserFormValues>({
    resolver: zodResolver(userSchema),
    defaultValues: {
      email: "",
      first_name: "",
      last_name: "",
      role: "OPERATOR",
      is_active: true,
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
      })
    } else if (userId === "new") {
      reset({
        email: "",
        first_name: "",
        last_name: "",
        role: "OPERATOR",
        is_active: true,
      })
    }
  }, [user, userId, reset])

  const saveMutation = useMutation({
    mutationFn: async (data: UserFormValues) => {
      if (isEditing) {
        return usersService.updateUser(userId!, data)
      } else {
        return usersService.createUser(data)
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
      onClose()
    }
  })

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
                  <SelectItem value="ADMIN">Admin (Full Access)</SelectItem>
                  <SelectItem value="MANAGER">Manager (View + Edit)</SelectItem>
                  <SelectItem value="OPERATOR">Operator (Limited Actions)</SelectItem>
                  <SelectItem value="VIEWER">Viewer (Read Only)</SelectItem>
                </SelectContent>
              </Select>
              {errors.role && <p className="text-xs text-destructive">{errors.role.message}</p>}
            </div>

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
