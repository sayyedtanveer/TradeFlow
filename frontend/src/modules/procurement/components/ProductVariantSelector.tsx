import { useEffect, useState } from "react"
import { productService } from "@/services/product.service"
import { materialService } from "@/services/material.service"
import type { ItemVariantSearchItem } from "@/types/product.types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { cn } from "@/lib/utils"

type Props = {
  /** FG material id used for receive API */
  value: string
  onChange: (materialId: string) => void
  label?: string
  disabled?: boolean
}

export function ProductVariantSelector({ value, onChange, label = "Finished goods variant", disabled }: Props) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState("")
  const [rows, setRows] = useState<ItemVariantSearchItem[]>([])
  const [loading, setLoading] = useState(false)
  const [displayLabel, setDisplayLabel] = useState("")

  useEffect(() => {
    if (!value) {
      setDisplayLabel("")
      return
    }
    materialService
      .getMaterial(value)
      .then((m) => setDisplayLabel(`${m.code} — ${m.name}`))
      .catch(() => setDisplayLabel(`${value.slice(0, 8)}…`))
  }, [value])

  useEffect(() => {
    if (!open) return
    let cancelled = false
    const t = setTimeout(() => {
      setLoading(true)
      productService
        .searchVariants({ search: q || undefined, page_size: 40 })
        .then((res) => {
          if (!cancelled) setRows(res.items)
        })
        .finally(() => {
          if (!cancelled) setLoading(false)
        })
    }, 280)
    return () => {
      cancelled = true
      clearTimeout(t)
    }
  }, [q, open])

  const pick = (row: ItemVariantSearchItem) => {
    const mid = row.stock_material_id
    if (!mid) return
    onChange(mid)
    setDisplayLabel(`${row.code} — ${row.name}`)
    setOpen(false)
  }

  return (
    <div className="space-y-2">
      {label && <Label>{label}</Label>}
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            className="w-full justify-start font-normal"
            disabled={disabled}
          >
            {displayLabel || (value ? `${value.slice(0, 8)}…` : "Search by code or name…")}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[min(100vw-2rem,28rem)] p-3" align="start">
          <Input
            placeholder="Search code or name…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="mb-2"
          />
          <div className="max-h-56 overflow-auto space-y-1 text-sm">
            {loading && <p className="text-muted-foreground">Loading…</p>}
            {!loading && rows.length === 0 && <p className="text-muted-foreground">No matches</p>}
            {rows.map((row) => (
              <button
                key={row.id}
                type="button"
                className={cn(
                  "w-full text-left rounded px-2 py-1.5 hover:bg-muted",
                  !row.stock_material_id && "opacity-50 cursor-not-allowed"
                )}
                disabled={!row.stock_material_id}
                onClick={() => pick(row)}
              >
                <div className="font-medium">{row.code}</div>
                <div className="text-xs text-muted-foreground truncate">{row.name}</div>
                {!row.stock_material_id && (
                  <div className="text-xs text-amber-700 dark:text-amber-500">
                    No FG material linked (use same UUID as variant or a finished material with matching code)
                  </div>
                )}
              </button>
            ))}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  )
}
