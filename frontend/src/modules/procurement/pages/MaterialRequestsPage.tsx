import { useEffect, useState } from "react"
import { supplyChainApi, type MaterialRequest } from "@/services/supply-chain.service"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useToast } from "@/hooks/use-toast"

export default function MaterialRequestsPage() {
  const { toast } = useToast()
  const [rows, setRows] = useState<MaterialRequest[]>([])
  const [running, setRunning] = useState(false)

  const load = () =>
    supplyChainApi.listMaterialRequests().then((r) => setRows(r.data))

  useEffect(() => {
    load().catch(() => toast({ title: "Failed to load requests", variant: "destructive" }))
  }, [toast])

  const runMrp = async () => {
    setRunning(true)
    try {
      const { data } = await supplyChainApi.runMrp()
      toast({ title: "MRP run complete", description: `${data.created} request(s) created` })
      await load()
    } catch {
      toast({ title: "MRP failed", variant: "destructive" })
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex flex-wrap justify-between gap-4 items-start">
        <div>
          <h1 className="text-2xl font-semibold">Material requests (MRP)</h1>
          <p className="text-sm text-muted-foreground">
            Run MRP to create requests when available + incoming − reserved falls below reorder + safety.
          </p>
        </div>
        <Button onClick={runMrp} disabled={running}>
          {running ? "Running…" : "Run MRP"}
        </Button>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Item</TableHead>
            <TableHead>Type</TableHead>
            <TableHead className="text-right">Required</TableHead>
            <TableHead className="text-right">Fulfilled</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r) => (
            <TableRow key={r.id}>
              <TableCell className="font-mono text-xs">{r.item_id}</TableCell>
              <TableCell>{r.item_type}</TableCell>
              <TableCell className="text-right">{r.required_quantity}</TableCell>
              <TableCell className="text-right">{r.fulfilled_quantity}</TableCell>
              <TableCell>{r.status}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {rows.length === 0 && <p className="text-sm text-muted-foreground">No material requests.</p>}
    </div>
  )
}
