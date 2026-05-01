import { useQuery } from "@tanstack/react-query"
import { usersService } from "@/services/users.service"
import { DataTable } from "@/components/shared/DataTable"
import { PageHeader } from "@/components/layout/PageHeader"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { TableSkeleton } from "@/components/shared/LoadingSkeleton"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Plus } from "lucide-react"
import { useSearchParams } from "react-router-dom"
import { ColumnDef } from "@tanstack/react-table"
import { User } from "@/types/auth.types"
import { UserFormDrawer } from "../components/UserFormDrawer"
import { RoleManagementPanel } from "../components/RoleManagementPanel"

export default function UserListPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const userId = searchParams.get("userId")
  const isDrawerOpen = userId !== null

  const handleCloseDrawer = () => {
    setSearchParams({})
  }

  const { data: users, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: () => usersService.getUsers(),
  })

  // Define columns for TanStack Table
  const columns: ColumnDef<User>[] = [
    {
      accessorKey: "first_name",
      header: "Name",
      cell: ({ row }) => (
        <div className="font-medium">{row.original.first_name} {row.original.last_name}</div>
      ),
    },
    {
      accessorKey: "email",
      header: "Email",
    },
    {
      accessorKey: "role",
      header: "Role",
      cell: ({ row }) => {
        const role = row.original.role
        const variant = role === "ADMIN" ? "default" : role === "MANAGER" ? "secondary" : "outline"
        return <StatusBadge status={"active"} className={variant === "outline" ? "bg-muted text-muted-foreground" : ""} label={role} />
      },
    },
    {
      accessorKey: "is_active",
      header: "Status",
      cell: ({ row }) => {
        const isActive = row.original.is_active
        return <StatusBadge status={isActive ? "active" : "inactive"} label={isActive ? "Active" : "Disabled"} />
      },
    },
    {
      id: "actions",
      cell: ({ row }) => {
        return (
          <Button variant="ghost" size="sm" onClick={() => setSearchParams({ userId: row.original.id })}>
            Edit
          </Button>
        )
      },
    },
  ]

  const actionButtons = (
    <Button onClick={() => setSearchParams({ userId: "new" })}>
      <Plus className="mr-2 h-4 w-4" />
      Invite User
    </Button>
  )

  return (
    <div className="w-full space-y-6">
      <PageHeader 
        title="User Management" 
        description="Manage access control, roles, and user accounts for your tenant."
        action={actionButtons}
      />

      <RoleManagementPanel />

      {isLoading ? (
        <TableSkeleton rows={5} />
      ) : (
        <>
          <div className="hidden md:block">
            <DataTable 
              columns={columns} 
              data={users || []} 
              searchKey="email" 
              searchPlaceholder="Search users by email..."
            />
          </div>
          <div className="md:hidden grid gap-4 grid-cols-1">
            {(users || []).map((user) => {
              const variant = user.role === "ADMIN" ? "default" : user.role === "MANAGER" ? "secondary" : "outline"
              
              return (
                <Card key={user.id} className="cursor-pointer hover:bg-accent/50 transition-colors" onClick={() => setSearchParams({ userId: user.id })}>
                  <CardContent className="p-4">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h3 className="font-medium text-base">{user.first_name} {user.last_name}</h3>
                        <p className="text-sm text-muted-foreground">{user.email}</p>
                      </div>
                      <StatusBadge 
                        status={user.is_active ? "active" : "inactive"} 
                        label={user.is_active ? "Active" : "Disabled"} 
                      />
                    </div>
                    <div className="flex items-center gap-2 mt-4 text-sm">
                      <span className="text-muted-foreground">Role:</span>
                      <StatusBadge 
                        status="active" 
                        className={variant === "outline" ? "bg-muted text-muted-foreground" : ""} 
                        label={user.role} 
                      />
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </>
      )}

      <UserFormDrawer 
        open={isDrawerOpen} 
        onClose={handleCloseDrawer} 
        userId={userId} 
      />
    </div>
  )
}
