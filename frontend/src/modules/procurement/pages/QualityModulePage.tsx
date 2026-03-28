import { useEffect, useState } from "react"
import { materialService } from "@/services/material.service"
import type { Location, Material } from "@/types/material.types"
import {
  supplyChainApi,
  type InspectionRow,
  type InspectionTemplate,
  type NCRRow,
  type QuarantineRow,
} from "@/services/supply-chain.service"
import { Checkbox } from "@/components/ui/checkbox"
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

  const [templates, setTemplates] = useState<InspectionTemplate[]>([])
  const [qLocations, setQLocations] = useState<(Location & { location_type?: string })[]>([])

  const [tplName, setTplName] = useState("")
  const [tplParamsText, setTplParamsText] = useState('[{"name": "dimension", "tolerance_min": null, "tolerance_max": null}]')

  const [qLocName, setQLocName] = useState("")
  const [qLocCode, setQLocCode] = useState("")
  const [qLocParent, setQLocParent] = useState("")

  const [qcMat, setQcMat] = useState("")
  const [qcInspReq, setQcInspReq] = useState(false)
  const [qcTpl, setQcTpl] = useState("")

  const loadAll = async () => {
    const [insp, n, q, mats, locs, tpls, qLocs] = await Promise.all([
      supplyChainApi.listInspections(),
      supplyChainApi.listNCRs(),
      supplyChainApi.quarantineStock(),
      materialService.getMaterials({ page: 1, page_size: 300 }),
      materialService.getLocations(),
      supplyChainApi.listInspectionTemplates(),
      materialService.getLocations({ type: "quarantine" }),
    ])
    setInspections(insp.data)
    setNcrs(n.data)
    setQuarantine(q.data)
    setMaterials(mats.items)
    setLocations(locs as (Location & { location_type?: string })[])
    setTemplates(tpls.data)
    setQLocations(qLocs as (Location & { location_type?: string })[])
    const wh = locs.find((l) => locKind(l as Location & { location_type?: string }) === "warehouse")
    if (wh) setWhId(wh.id)
  }

  useEffect(() => {
    if (!qcMat) {
      setQcInspReq(false)
      setQcTpl("")
      return
    }
    materialService
      .getMaterial(qcMat)
      .then((m) => {
        setQcInspReq(!!m.inspection_required)
        setQcTpl(m.inspection_template_id || "")
      })
      .catch(() => {})
  }, [qcMat])

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

  const createTemplate = async () => {
    if (!tplName.trim()) {
      toast({ title: "Template name required", variant: "destructive" })
      return
    }
    let params: Record<string, unknown>[]
    try {
      params = JSON.parse(tplParamsText) as Record<string, unknown>[]
      if (!Array.isArray(params)) throw new Error("not array")
    } catch {
      toast({ title: "Parameters must be a JSON array", variant: "destructive" })
      return
    }
    try {
      await supplyChainApi.createInspectionTemplate({ name: tplName.trim(), parameters: params, is_active: true })
      toast({ title: "Template created" })
      setTplName("")
      await loadAll()
    } catch {
      toast({ title: "Create failed", variant: "destructive" })
    }
  }

  const createQuarantineLocation = async () => {
    if (!qLocName.trim()) {
      toast({ title: "Location name required", variant: "destructive" })
      return
    }
    try {
      await materialService.createLocation({
        name: qLocName.trim(),
        type: "quarantine",
        code: qLocCode.trim() || undefined,
        parent_id: qLocParent || undefined,
        is_active: true,
      })
      toast({ title: "Quarantine location created" })
      setQLocName("")
      setQLocCode("")
      setQLocParent("")
      await loadAll()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast({ title: detail || "Create failed", variant: "destructive" })
    }
  }

  const saveMaterialQc = async () => {
    if (!qcMat) {
      toast({ title: "Select a material", variant: "destructive" })
      return
    }
    try {
      await materialService.updateMaterial(qcMat, {
        inspection_required: qcInspReq,
        inspection_template_id: qcTpl || null,
      })
      toast({ title: "Material QC settings saved" })
      await loadAll()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast({ title: detail || "Save failed", variant: "destructive" })
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

  const parentName = (pid: string | null | undefined) => {
    if (!pid) return "—"
    const p = locations.find((x) => x.id === pid)
    return p?.name ?? pid.slice(0, 8)
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-semibold">Quality &amp; quarantine</h1>
        <p className="text-sm text-muted-foreground">
          Pass moves pending → available. Fail moves pending → quarantine (needs a location with type quarantine).
        </p>
      </div>

      <Tabs defaultValue="inspect">
        <TabsList className="flex flex-wrap h-auto gap-1">
          <TabsTrigger value="inspect">New inspection</TabsTrigger>
          <TabsTrigger value="history">Inspections</TabsTrigger>
          <TabsTrigger value="ncr">NCR</TabsTrigger>
          <TabsTrigger value="quarantine">Quarantine stock</TabsTrigger>
          <TabsTrigger value="q-locations">Quarantine locations</TabsTrigger>
          <TabsTrigger value="templates">Inspection templates</TabsTrigger>
          <TabsTrigger value="material-qc">Material QC</TabsTrigger>
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

        <TabsContent value="q-locations" className="space-y-6">
          <div className="border rounded-lg p-4 space-y-3 max-w-lg">
            <h3 className="font-medium">Create quarantine location</h3>
            <p className="text-xs text-muted-foreground">
              Used when inspection fails and stock must move to a quarantine bucket.
            </p>
            <div className="space-y-2">
              <Label>Name</Label>
              <Input value={qLocName} onChange={(e) => setQLocName(e.target.value)} placeholder="e.g. Q1 — incoming hold" />
            </div>
            <div className="space-y-2">
              <Label>Code (optional)</Label>
              <Input value={qLocCode} onChange={(e) => setQLocCode(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Parent warehouse (optional)</Label>
              <Select value={qLocParent || "__none__"} onValueChange={(v) => setQLocParent(v === "__none__" ? "" : v)}>
                <SelectTrigger>
                  <SelectValue placeholder="None" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">(none)</SelectItem>
                  {warehouses.map((l) => (
                    <SelectItem key={l.id} value={l.id}>
                      {l.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button type="button" onClick={createQuarantineLocation}>
              Create location
            </Button>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Code</TableHead>
                <TableHead>Parent</TableHead>
                <TableHead>Active</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {qLocations.map((l) => (
                <TableRow key={l.id}>
                  <TableCell>{l.name}</TableCell>
                  <TableCell className="font-mono text-xs">{l.code || "—"}</TableCell>
                  <TableCell>{parentName(l.parent_location_id ?? l.parent_id)}</TableCell>
                  <TableCell>{l.is_active ? "yes" : "no"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {qLocations.length === 0 && (
            <p className="text-sm text-muted-foreground">No quarantine locations yet.</p>
          )}
        </TabsContent>

        <TabsContent value="templates" className="space-y-6">
          <div className="border rounded-lg p-4 space-y-3 max-w-xl">
            <h3 className="font-medium">New template</h3>
            <div className="space-y-2">
              <Label>Name</Label>
              <Input value={tplName} onChange={(e) => setTplName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Parameters (JSON array)</Label>
              <Textarea value={tplParamsText} onChange={(e) => setTplParamsText(e.target.value)} rows={5} className="font-mono text-xs" />
            </div>
            <Button type="button" onClick={createTemplate}>
              Create template
            </Button>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Parameters</TableHead>
                <TableHead>Active</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {templates.map((t) => (
                <TableRow key={t.id}>
                  <TableCell>{t.name}</TableCell>
                  <TableCell className="font-mono text-xs max-w-md truncate">
                    {Array.isArray(t.parameters) ? `${t.parameters.length} row(s)` : "—"}
                  </TableCell>
                  <TableCell>{t.is_active ? "yes" : "no"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {templates.length === 0 && (
            <p className="text-sm text-muted-foreground">No inspection templates yet.</p>
          )}
        </TabsContent>

        <TabsContent value="material-qc" className="space-y-4 max-w-lg border rounded-lg p-4">
          <h3 className="font-medium">Link material to inspection</h3>
          <p className="text-xs text-muted-foreground">
            Set whether receiving/inspection is required and which template applies.
          </p>
          <div className="space-y-2">
            <Label>Material</Label>
            <Select value={qcMat} onValueChange={setQcMat}>
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
          <div className="flex items-center gap-2">
            <Checkbox
              id="insp-req"
              checked={qcInspReq}
              onCheckedChange={(v) => setQcInspReq(v === true)}
            />
            <Label htmlFor="insp-req" className="font-normal cursor-pointer">
              Inspection required
            </Label>
          </div>
          <div className="space-y-2">
            <Label>Inspection template</Label>
            <Select value={qcTpl || "__none__"} onValueChange={(v) => setQcTpl(v === "__none__" ? "" : v)}>
              <SelectTrigger>
                <SelectValue placeholder="None" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">(none)</SelectItem>
                {templates.map((t) => (
                  <SelectItem key={t.id} value={t.id}>
                    {t.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button type="button" onClick={saveMaterialQc}>
            Save
          </Button>
        </TabsContent>
      </Tabs>
    </div>
  )
}
