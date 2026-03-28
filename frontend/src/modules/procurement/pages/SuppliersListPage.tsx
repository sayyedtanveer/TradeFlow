import { useEffect, useState } from "react"
import { supplyChainApi, type Supplier } from "@/services/supply-chain.service"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Checkbox } from "@/components/ui/checkbox"
import { useToast } from "@/hooks/use-toast"
import { Pencil, Plus } from "lucide-react"

export default function SuppliersListPage() {
  const { toast } = useToast()
  const [items, setItems] = useState<Supplier[]>([])
  const [code, setCode] = useState("")
  const [name, setName] = useState("")
  const [open, setOpen] = useState(false)

  const [editOpen, setEditOpen] = useState(false)
  const [editing, setEditing] = useState<Supplier | null>(null)
  const [editName, setEditName] = useState("")
  const [editEmail, setEditEmail] = useState("")
  const [editPhone, setEditPhone] = useState("")
  const [editActive, setEditActive] = useState(true)

  const load = () => supplyChainApi.listSuppliers().then((r) => setItems(r.data))

  useEffect(() => {
    load().catch(() => toast({ title: "Failed to load suppliers", variant: "destructive" }))
  }, [toast])

  const create = async () => {
    if (!code.trim() || !name.trim()) return
    try {
      await supplyChainApi.createSupplier({ code: code.trim(), name: name.trim() })
      setCode("")
      setName("")
      setOpen(false)
      await load()
      toast({ title: "Supplier created" })
    } catch {
      toast({ title: "Create failed", variant: "destructive" })
    }
  }

  const openEdit = (s: Supplier) => {
    setEditing(s)
    setEditName(s.name)
    setEditEmail(s.email || "")
    setEditPhone(s.phone || "")
    setEditActive(s.is_active)
    setEditOpen(true)
  }

  const saveEdit = async () => {
    if (!editing) return
    try {
      await supplyChainApi.updateSupplier(editing.id, {
        name: editName,
        email: editEmail || undefined,
        phone: editPhone || undefined,
        is_active: editActive,
      })
      toast({ title: "Supplier updated" })
      setEditOpen(false)
      await load()
    } catch {
      toast({ title: "Update failed", variant: "destructive" })
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold">Suppliers</h1>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Add supplier
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>New supplier</DialogTitle>
            </DialogHeader>
            <div className="space-y-3 py-2">
              <div className="space-y-2">
                <Label>Code</Label>
                <Input value={code} onChange={(e) => setCode(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Name</Label>
                <Input value={name} onChange={(e) => setName(e.target.value)} />
              </div>
            </div>
            <DialogFooter>
              <Button onClick={create}>Save</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Code</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Email</TableHead>
            <TableHead>Active</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((s) => (
            <TableRow key={s.id}>
              <TableCell className="font-medium">{s.code}</TableCell>
              <TableCell>{s.name}</TableCell>
              <TableCell>{s.email || "—"}</TableCell>
              <TableCell>{s.is_active ? "Yes" : "No"}</TableCell>
              <TableCell className="text-right">
                <Button variant="ghost" size="icon" onClick={() => openEdit(s)}>
                  <Pencil className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit supplier</DialogTitle>
          </DialogHeader>
          {editing && (
            <div className="space-y-3 py-2">
              <p className="text-sm text-muted-foreground font-mono">{editing.code}</p>
              <div className="space-y-2">
                <Label>Name</Label>
                <Input value={editName} onChange={(e) => setEditName(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Email</Label>
                <Input value={editEmail} onChange={(e) => setEditEmail(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Phone</Label>
                <Input value={editPhone} onChange={(e) => setEditPhone(e.target.value)} />
              </div>
              <div className="flex items-center gap-2">
                <Checkbox id="active" checked={editActive} onCheckedChange={(v) => setEditActive(!!v)} />
                <Label htmlFor="active">Active</Label>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button onClick={saveEdit}>Save changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
