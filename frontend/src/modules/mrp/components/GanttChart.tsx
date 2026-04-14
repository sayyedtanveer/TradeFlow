import { useMemo, useRef, useState } from "react"
import { GanttEntry } from "../../../services/mrp.service"

// ── colour helpers ────────────────────────────────────────────────────────── #
const statusColour: Record<string, string> = {
  PLANNED: "#6366f1",
  RELEASED: "#0ea5e9",
  IN_PROGRESS: "#f59e0b",
  COMPLETED: "#22c55e",
  CLOSED: "#6b7280",
}

const priorityBorder: Record<string, string> = {
  LOW: "#6b7280",
  NORMAL: "#6366f1",
  HIGH: "#f59e0b",
  URGENT: "#ef4444",
}

// ── Types ─────────────────────────────────────────────────────────────────── #
interface Props {
  entries: GanttEntry[]
  onReschedule?: (id: string, newStart: string, newDue: string) => void
}

// ── Helper: parse ISO date string → Date (midnight UTC) ───────────────────── #
function parseDate(s: string): Date {
  const [y, m, d] = s.split("-").map(Number)
  return new Date(Date.UTC(y, m - 1, d))
}

function formatDate(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function addDays(d: Date, n: number): Date {
  const r = new Date(d)
  r.setUTCDate(r.getUTCDate() + n)
  return r
}

// ── GanttChart ────────────────────────────────────────────────────────────── #
export default function GanttChart({ entries, onReschedule }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dragging, setDragging] = useState<string | null>(null)
  const [tooltip, setTooltip] = useState<{ entry: GanttEntry; x: number; y: number } | null>(null)

  // ── Date range from entries ──────────────────────────────────────────────
  const { chartStart, headerDays } = useMemo(() => {
    if (!entries.length) {
      const today = new Date()
      const cs = new Date(Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()))
      return { chartStart: cs, totalDays: 30, headerDays: buildHeaderDays(cs, 30) }
    }
    const starts = entries.map((e) => parseDate(e.start_date))
    const dues = entries.map((e) => parseDate(e.due_date))
    const minD = new Date(Math.min(...starts.map((d) => d.getTime())))
    const maxD = new Date(Math.max(...dues.map((d) => d.getTime())))
    const pad = 7
    const cs = addDays(minD, -pad)
    const total = Math.ceil((maxD.getTime() - cs.getTime()) / 86_400_000) + pad * 2
    return { chartStart: cs, headerDays: buildHeaderDays(cs, total) }
  }, [entries])

  const DAY_PX = 36 // pixels per day
  const ROW_H = 52

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div style={{ overflowX: "auto", position: "relative" }} ref={containerRef}>
      {/* Header — day labels */}
      <div
        style={{
          display: "flex",
          marginLeft: 200,
          borderBottom: "1px solid rgba(255,255,255,0.1)",
          position: "sticky",
          top: 0,
          zIndex: 10,
          background: "#0f1117",
        }}
      >
        {headerDays.map((d, i) => {
          const isWeekend = d.getUTCDay() === 0 || d.getUTCDay() === 6
          const isToday = formatDate(d) === formatDate(new Date())
          return (
            <div
              key={i}
              style={{
                width: DAY_PX,
                minWidth: DAY_PX,
                textAlign: "center",
                fontSize: 10,
                padding: "6px 0",
                color: isToday ? "#818cf8" : isWeekend ? "#6b7280" : "#9ca3af",
                fontWeight: isToday ? 700 : 400,
                borderRight: "1px solid rgba(255,255,255,0.04)",
                background: isWeekend ? "rgba(255,255,255,0.02)" : undefined,
              }}
            >
              {d.getUTCDate()}
              {d.getUTCDate() === 1 && (
                <div style={{ fontSize: 8, color: "#6366f1", fontWeight: 600 }}>
                  {d.toLocaleString("default", { month: "short" })}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Rows */}
      {entries.map((entry, rowIdx) => {
        const startD = parseDate(entry.start_date)
        const dueD = parseDate(entry.due_date)
        const startOff = Math.round((startD.getTime() - chartStart.getTime()) / 86_400_000)
        const durDays = Math.max(
          Math.round((dueD.getTime() - startD.getTime()) / 86_400_000) + 1,
          1
        )
        const barColor = statusColour[entry.status] ?? "#6366f1"
        const borderColor = priorityBorder[entry.priority] ?? "#6366f1"

        return (
          <div
            key={entry.id}
            style={{
              display: "flex",
              alignItems: "center",
              height: ROW_H,
              borderBottom: "1px solid rgba(255,255,255,0.05)",
              background: rowIdx % 2 === 0 ? "rgba(255,255,255,0.01)" : "transparent",
            }}
          >
            {/* Label */}
            <div
              style={{
                width: 200,
                minWidth: 200,
                padding: "0 12px",
                overflow: "hidden",
                whiteSpace: "nowrap",
              }}
            >
              <div style={{ fontSize: 12, fontWeight: 600, color: "#e5e7eb" }}>
                {entry.wo_number}
              </div>
              <div style={{ fontSize: 10, color: "#9ca3af" }}>
                {entry.status.replace("_", " ")} · {entry.priority}
              </div>
            </div>

            {/* Timeline */}
            <div style={{ position: "relative", flex: 1, height: ROW_H }}>
              {/* Weekend shading */}
              {headerDays.map((d, i) => {
                const isWE = d.getUTCDay() === 0 || d.getUTCDay() === 6
                return isWE ? (
                  <div
                    key={i}
                    style={{
                      position: "absolute",
                      left: i * DAY_PX,
                      width: DAY_PX,
                      height: "100%",
                      background: "rgba(255,255,255,0.015)",
                    }}
                  />
                ) : null
              })}

              {/* Gantt bar */}
              <div
                draggable
                onDragStart={() => setDragging(entry.id)}
                onDragEnd={(e) => {
                  if (!onReschedule || !containerRef.current) return
                  setDragging(null)
                  const rect = containerRef.current.getBoundingClientRect()
                  const offsetX = e.clientX - rect.left - 200
                  const newStartOff = Math.round(offsetX / DAY_PX)
                  const delta = newStartOff - startOff
                  const ns = formatDate(addDays(startD, delta))
                  const nd = formatDate(addDays(dueD, delta))
                  onReschedule(entry.id, ns, nd)
                }}
                onMouseEnter={(e) => setTooltip({ entry, x: e.clientX, y: e.clientY })}
                onMouseLeave={() => setTooltip(null)}
                style={{
                  position: "absolute",
                  left: startOff * DAY_PX,
                  width: durDays * DAY_PX - 2,
                  top: "50%",
                  transform: "translateY(-50%)",
                  height: 28,
                  borderRadius: 6,
                  background: `${barColor}cc`,
                  borderLeft: `3px solid ${borderColor}`,
                  cursor: "grab",
                  overflow: "hidden",
                  display: "flex",
                  alignItems: "center",
                  paddingLeft: 6,
                  transition: "box-shadow 0.15s",
                  boxShadow:
                    dragging === entry.id
                      ? `0 0 0 2px ${barColor}, 0 4px 16px rgba(0,0,0,0.4)`
                      : "0 1px 4px rgba(0,0,0,0.3)",
                }}
              >
                {/* Progress fill */}
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    width: `${entry.progress_pct}%`,
                    background: `${barColor}55`,
                    borderRadius: "inherit",
                  }}
                />
                <span
                  style={{
                    position: "relative",
                    fontSize: 10,
                    fontWeight: 600,
                    color: "#fff",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                  }}
                >
                  {entry.wo_number} · {entry.progress_pct}%
                </span>
              </div>
            </div>
          </div>
        )
      })}

      {/* Tooltip */}
      {tooltip && (
        <div
          style={{
            position: "fixed",
            left: tooltip.x + 12,
            top: tooltip.y - 8,
            zIndex: 9999,
            background: "#1e2130",
            border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: 8,
            padding: "10px 14px",
            pointerEvents: "none",
            minWidth: 220,
            boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
          }}
        >
          <div style={{ fontWeight: 700, color: "#e5e7eb", marginBottom: 4 }}>
            {tooltip.entry.wo_number}
          </div>
          <div style={{ fontSize: 12, color: "#9ca3af", lineHeight: 1.7 }}>
            <div>Status: {tooltip.entry.status.replace("_", " ")}</div>
            <div>Priority: {tooltip.entry.priority}</div>
            <div>
              {tooltip.entry.start_date} → {tooltip.entry.due_date}
            </div>
            <div>
              Progress: {tooltip.entry.produced_quantity} / {tooltip.entry.planned_quantity} (
              {tooltip.entry.progress_pct}%)
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── helpers ─────────────────────────────────────────────────────────────────

function buildHeaderDays(start: Date, total: number): Date[] {
  return Array.from({ length: total }, (_, i) => {
    const d = new Date(start)
    d.setUTCDate(d.getUTCDate() + i)
    return d
  })
}
