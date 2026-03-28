import { useEffect, useState } from "react"
import { materialService } from "@/services/material.service"
import type { Location, Material } from "@/types/material.types"
import {
  supplyChainApi,
  type InspectionRow,
  type NCRRow,
  type QuarantineRow,
} from "@/services/supply-chain.service"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/hooks/use-toast"

function locKind(l: Location & { location_type?: string }) {
  return l.location_type ?? (l as { type?: string }).type ?? ""
}

export default function QualityModulePage() {
  const { toast } = useToast()
  const [inspections, setInspections] = useState<InspectionRow[]>([])
  const [ncrs, setNcrs] = useState<NCRRow[]>([])
  const [quarantine, setQuarantine] = useState<QuarantineRow[]>([])
  const [materials, setMaterials] = useState<Material[]>([])
  const [locations, setLocations] = useState<(Location & { location_type?: string })[]>([])

  const [refId, setRefId] = useState("")
  const [matId, setMatId] = useState("")
  const [whId, setWhId] = useState("")
  const [qty, setQty] = useState("1")
  const [result, setResult] = useState<"pass" | "fail">("pass")
  const [remarks, setRemarks] = useState("")

  const [ncrInspectionId, setNcrInspectionId] = useState("")
  const [ncrType, setNcrType] = useState("rework")
  const [ncrReason, setNcrReason] = useState("")
  const [ncrAction, setNcrAction] = useState("")

  const loadAll = async () => {
    const [insp, n, q, mats, locs] = await Promise.all([
      supplyChainApi.listInspections(),
      supplyChainApi.listNCRs(),
      supplyChainApi.quarantineStock(),
      materialService.getMaterials({ page: 1, page_size: 300 }),
      materialService.getLocations(),
    ])
    setInspections(insp.data)
    setNcrs(n.data)
    setQuarantine(q.data)
    setMaterials(mats.items)
    setLocations(locs as (Location & { location_type?: string })[])
    const wh = locs.find((l) => locKind(l as Location & { location_type?: string }) === "warehouse")
    if (wh) setWhId(wh.id)
  }

  useEffect(() => {
    loadAll().catch(() => toast({ title: "Failed to load quality data", variant: "destructive" }))
  }, [toast])

  const submitInspection = async () => {
    if (!refId || !matId || !whId || !qty) {
      toast({ title: "Fill reference id, material, warehouse, quantity", variant: "destructive" })
      return
    }
    try {
      await supplyChainApi.qualityInspect({
        reference_type: "purchase_receipt",
        reference_id: refId,
        material_id: matId,
        quantity: Number(qty),
        warehouse_location_id: whId,
        result,
        remarks: remarks || undefined,
      })
      toast({ title: "Inspection recorded" })
      await loadAll()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast({ title: detail || "Inspection failed", variant: "destructive" })
    }
  }

  const submitNCR = async () => {
    if (!ncrInspectionId) {
      toast({ title: "Inspection id required", variant: "destructive" })
      return
    }
    try {
      await supplyChainApi.createNCR({
        inspection_id: ncrInspectionId,
        ncr_type: ncrType,
        reason: ncrReason || undefined,
        action_taken: ncrAction || undefined,
      })
      toast({ title: "NCR created" })
      await loadAll()
    } catch {
      toast({ title: "NCR failed", variant: "destructive" })
    }
  }

  const warehouses = locations.filter((l) => locKind(l) === "warehouse" && l.is_active)

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-semibold">Quality &amp; quarantine</h1>
        <p className="text-sm text-muted-foreground">
          Pass moves pending → available. Fail moves pending → quarantine (needs a location with type quarantine).
        </p>
      </div>

      <Tabs defaultValue="inspect">
        <TabsList>
          <TabsTrigger value="inspect">New inspection</TabsTrigger>
          <TabsTrigger value="history">Inspections</TabsTrigger>
          <TabsTrigger value="ncr">NCR</TabsTrigger>
          <TabsTrigger value="quarantine">Quarantine stock</TabsTrigger>
        </TabsList>

        <TabsContent value="inspect" className="space-y-4 border rounded-lg p-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Reference ID (e.g. PO line UUID)</Label>
              <Input value={refId} onChange={(e) => setRefId(e.target.value)} placeholder="uuid" />
            </div>
            <div className="space-y-2">
              <Label>Material</Label>
              <Select value={matId} onValueChange={setMatId}>
                <SelectTrigger>
                  <SelectValue placeholder="Material" />
                </SelectTrigger>
                <SelectContent>
                  {materials.map((m) => (
                    <SelectItem key={m.id} value={m.id}>
                      {m.code} — {m.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Warehouse (pending stock bucket)</Label>
              <Select value={whId} onValueChange={setWhId}>
                <SelectTrigger>
                  <SelectValue placeholder="Warehouse" />
                </SelectTrigger>
                <SelectContent>
                  {warehouses.map((l) => (
                    <SelectItem key={l.id} value={l.id}>
                      {l.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Quantity</Label>
              <Input type="number" value={qty} onChange={(e) => setQty(e.target.value)} />
            </div>
          </div>
          <div className="flex gap-2">
            <Button type="button" variant={result === "pass" ? "default" : "outline"} onClick={() => setResult("pass")}>
              Pass
            </Button>
            <Button type="button" variant={result === "fail" ? "destructive" : "outline"} onClick={() => setResult("fail")}>
              Fail → quarantine
            </Button>
          </div>
          <div className="space-y-2">
            <Label>Remarks</Label>
            <Textarea value={remarks} onChange={(e) => setRemarks(e.target.value)} rows={2} />
          </div>
          <Button onClick={submitInspection}>Submit inspection</Button>
        </TabsContent>

        <TabsContent value="history">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Ref</TableHead>
                <TableHead>Result</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {inspections.map((x) => (
                <TableRow key={x.id}>
                  <TableCell>{x.inspection_date}</TableCell>
                  <TableCell className="font-mono text-xs">{x.reference_id}</TableCell>
                  <TableCell>{x.result}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {inspections.length === 0 && <p className="text-sm text-muted-foreground">No inspections yet.</p>}
        </TabsContent>

        <TabsContent value="ncr" className="space-y-6">
          <div className="border rounded-lg p-4 space-y-3 max-w-md">
            <h3 className="font-medium">Create NCR</h3>
            <div className="space-y-2">
              <Label>Inspection ID</Label>
              <Input value={ncrInspectionId} onChange={(e) => setNcrInspectionId(e.target.value)} placeholder="uuid" />
            </div>
            <div className="space-y-2">
              <Label>Type</Label>
              <Select value={ncrType} onValueChange={setNcrType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="rework">rework</SelectItem>
                  <SelectItem value="scrap">scrap</SelectItem>
                  <SelectItem value="reject">reject</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Reason</Label>
              <Textarea value={ncrReason} onChange={(e) => setNcrReason(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Action taken</Label>
              <Textarea value={ncrAction} onChange={(e) => setNcrAction(e.target.value)} />
            </div>
            <Button onClick={submitNCR}>Save NCR</Button>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead>Reason</TableHead>
                <TableHead>Inspection</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {ncrs.map((x) => (
                <TableRow key={x.id}>
                  <TableCell>{x.ncr_type}</TableCell>
                  <TableCell className="max-w-xs truncate">{x.reason}</TableCell>
                  <TableCell className="font-mono text-xs">{x.inspection_id}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TabsContent>

        <TabsContent value="quarantine">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Material</TableHead>
                <TableHead>Location</TableHead>
                <TableHead className="text-right">Qty</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {quarantine.map((row, i) => (
                <TableRow key={`${row.material_id}-${row.location_id}-${i}`}>
                  <TableCell>
                    {row.material_code} — {row.material_name}
                  </TableCell>
                  <TableCell>{row.location_name}</TableCell>
                  <TableCell className="text-right">{row.quantity}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {quarantine.length === 0 && (
            <p className="text-sm text-muted-foreground">No stock in quarantine.</p>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
