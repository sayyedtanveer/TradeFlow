import { useCallback, useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { mrpApi, WorkstationLoad, Bottleneck, GanttEntry } from "../../../services/mrp.service"
import GanttChart from "../components/GanttChart"

// ── helpers ──────────────────────────────────────────────────────────────── #
function today() {
  return new Date().toISOString().slice(0, 10)
}
function addDays(iso: string, n: number) {
  const d = new Date(iso)
  d.setDate(d.getDate() + n)
  return d.toISOString().slice(0, 10)
}

function DateBar({
  start,
  end,
  onChange,
}: {
  start: string
  end: string
  onChange: (s: string, e: string) => void
}) {
  const presets = [
    { label: "Today", s: today(), e: today() },
    { label: "This Week", s: today(), e: addDays(today(), 6) },
    { label: "This Month", s: today(), e: addDays(today(), 29) },
    { label: "3 Months", s: today(), e: addDays(today(), 89) },
  ]
  return (
    <div className="cap-datebar">
      {presets.map((p) => (
        <button
          key={p.label}
          className={`cap-preset${start === p.s && end === p.e ? " cap-preset--active" : ""}`}
          onClick={() => onChange(p.s, p.e)}
        >
          {p.label}
        </button>
      ))}
      <input
        type="date"
        value={start}
        onChange={(e) => onChange(e.target.value, end)}
        className="cap-input"
      />
      <span style={{ color: "#6b7280", fontSize: 13 }}>→</span>
      <input
        type="date"
        value={end}
        onChange={(e) => onChange(start, e.target.value)}
        className="cap-input"
      />
    </div>
  )
}

// ── Load bar component ────────────────────────────────────────────────────── #
function LoadBar({ row }: { row: WorkstationLoad }) {
  const clamp = Math.min(row.load_pct, 120)
  const colour =
    row.status === "critical"
      ? "#ef4444"
      : row.status === "warning"
      ? "#f59e0b"
      : "#22c55e"

  return (
    <div className="cap-load-row">
      <div className="cap-load-label">
        <span className="cap-ws-code">{row.workstation_code}</span>
        <span className="cap-ws-name">{row.workstation_name}</span>
      </div>
      <div className="cap-bar-wrap">
        {/* 70% marker */}
        <div className="cap-marker cap-marker--70" />
        {/* 90% marker */}
        <div className="cap-marker cap-marker--90" />
        {/* 100% marker */}
        <div className="cap-marker cap-marker--100" />

        <div
          className="cap-bar-fill"
          style={{
            width: `${(clamp / 120) * 100}%`,
            background: colour,
            boxShadow: row.load_pct > 90 ? `0 0 12px ${colour}66` : undefined,
          }}
        />
      </div>
      <div className="cap-load-stats">
        <span style={{ color: colour, fontWeight: 700, fontSize: 14 }}>
          {row.load_pct.toFixed(1)}%
        </span>
        <span style={{ color: "#6b7280", fontSize: 11 }}>
          {row.scheduled_hours}h / {row.capacity_hours}h
        </span>
      </div>
      <div
        className={`cap-badge cap-badge--${row.status}`}
      >
        {row.status.toUpperCase()}
      </div>
    </div>
  )
}

// ── Bottleneck card ───────────────────────────────────────────────────────── #
function BottleneckCard({ b }: { b: Bottleneck }) {
  return (
    <div
      className={`cap-alert-card cap-alert-card--${b.alert_level}`}
    >
      <div className="cap-alert-header">
        <span className="cap-alert-icon">
          {b.alert_level === "critical" ? "🚨" : "⚠️"}
        </span>
        <span className="cap-alert-title">{b.workstation_name}</span>
        <span className="cap-alert-pct" style={{ color: b.alert_level === "critical" ? "#ef4444" : "#f59e0b" }}>
          {b.load_pct.toFixed(1)}% load
        </span>
      </div>
      <p className="cap-alert-suggestion">{b.suggestion}</p>
      {b.overtime_hours_needed > 0 && (
        <div className="cap-alert-overtime">
          Overtime needed: <strong>{b.overtime_hours_needed}h</strong>
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────── #
export default function CapacityLoadChart() {
  const [start, setStart] = useState(today())
  const [end, setEnd] = useState(addDays(today(), 29))
  const [loadData, setLoadData] = useState<WorkstationLoad[]>([])
  const [bottlenecks, setBottlenecks] = useState<Bottleneck[]>([])
  const [schedule, setSchedule] = useState<GanttEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<"chart" | "gantt" | "alerts">("chart")
  const [error, setError] = useState<string | null>(null)

  const fetchAll = useCallback(async (s: string, e: string) => {
    setLoading(true)
    setError(null)
    try {
      const [loads, bns, sched] = await Promise.all([
        mrpApi.getLoadChart(s, e),
        mrpApi.getBottlenecks(),
        mrpApi.getSchedule(s, e),
      ])
      setLoadData(loads)
      setBottlenecks(bns)
      setSchedule(sched)
    } catch (err: any) {
      setError(err?.message ?? "Failed to load capacity data")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAll(start, end)
  }, []) // eslint-disable-line

  const handleDateChange = (s: string, e: string) => {
    setStart(s)
    setEnd(e)
    fetchAll(s, e)
  }

  const handleReschedule = async (id: string, newStart: string, newDue: string) => {
    try {
      await mrpApi.reschedule({ work_order_id: id, new_start: newStart, new_due: newDue })
      fetchAll(start, end)
    } catch {
      // ignore
    }
  }

  const okCount = loadData.filter((r) => r.status === "ok").length
  const warnCount = loadData.filter((r) => r.status === "warning").length
  const critCount = loadData.filter((r) => r.status === "critical").length
  const avgLoad =
    loadData.length > 0
      ? (loadData.reduce((a, b) => a + b.load_pct, 0) / loadData.length).toFixed(1)
      : "0"

  return (
    <div className="cap-page">
      <style>{CSS}</style>

      {/* ── Header ── */}
      <div className="cap-header">
        <div>
          <nav className="cap-breadcrumb">
            <Link to="/mrp" className="cap-breadcrumb-link">Capacity & MRP</Link>
            <span className="cap-breadcrumb-sep">›</span>
            <span>Capacity Load Chart</span>
          </nav>
          <h1 className="cap-title">Capacity Planning</h1>
          <p className="cap-subtitle">Workstation load, bottleneck detection &amp; production scheduling</p>
        </div>
        <button
          className="cap-btn-refresh"
          onClick={() => fetchAll(start, end)}
          disabled={loading}
        >
          {loading ? "⟳ Loading…" : "↺ Refresh"}
        </button>
      </div>

      {/* ── KPI cards ── */}
      <div className="cap-kpi-row">
        {[
          { label: "Workstations", value: loadData.length, color: "#6366f1" },
          { label: "Avg Load", value: `${avgLoad}%`, color: "#0ea5e9" },
          { label: "OK (<70%)", value: okCount, color: "#22c55e" },
          { label: "Warning (70–90%)", value: warnCount, color: "#f59e0b" },
          { label: "Critical (>90%)", value: critCount, color: "#ef4444" },
        ].map((k) => (
          <div key={k.label} className="cap-kpi-card">
            <div className="cap-kpi-value" style={{ color: k.color }}>{k.value}</div>
            <div className="cap-kpi-label">{k.label}</div>
          </div>
        ))}
      </div>

      {/* ── Date bar ── */}
      <DateBar start={start} end={end} onChange={handleDateChange} />

      {/* ── Tabs ── */}
      <div className="cap-tabs">
        {(["chart", "gantt", "alerts"] as const).map((t) => (
          <button
            key={t}
            className={`cap-tab${activeTab === t ? " cap-tab--active" : ""}`}
            onClick={() => setActiveTab(t)}
          >
            {t === "chart" ? "📊 Load Chart" : t === "gantt" ? "📅 Gantt Schedule" : `🚨 Bottlenecks (${bottlenecks.length})`}
          </button>
        ))}
      </div>

      {error && (
        <div className="cap-error">{error}</div>
      )}

      {/* ── Content panels ── */}
      {activeTab === "chart" && (
        <div className="cap-panel">
          <div className="cap-panel-legend">
            <span className="cap-legend-dot" style={{ background: "#22c55e" }} /> &lt;70% OK
            <span className="cap-legend-dot" style={{ background: "#f59e0b", marginLeft: 16 }} /> 70–90% Warning
            <span className="cap-legend-dot" style={{ background: "#ef4444", marginLeft: 16 }} /> &gt;90% Critical
          </div>
          {loading ? (
            <div className="cap-loading">Loading workstation data…</div>
          ) : loadData.length === 0 ? (
            <div className="cap-empty">No workstation data for this period.</div>
          ) : (
            <div className="cap-load-list">
              {loadData.map((row) => (
                <LoadBar key={row.workstation_id} row={row} />
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "gantt" && (
        <div className="cap-panel" style={{ padding: 0, overflow: "hidden" }}>
          {loading ? (
            <div className="cap-loading">Loading schedule…</div>
          ) : schedule.length === 0 ? (
            <div className="cap-empty">No work orders scheduled in this period.</div>
          ) : (
            <GanttChart entries={schedule} onReschedule={handleReschedule} />
          )}
        </div>
      )}

      {activeTab === "alerts" && (
        <div className="cap-panel">
          {loading ? (
            <div className="cap-loading">Analyzing bottlenecks…</div>
          ) : bottlenecks.length === 0 ? (
            <div className="cap-empty cap-empty--good">
              ✅ No bottlenecks detected — all workstations are within capacity.
            </div>
          ) : (
            <div className="cap-alerts-list">
              {bottlenecks.map((b) => (
                <BottleneckCard key={b.workstation_id} b={b} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Scoped CSS ────────────────────────────────────────────────────────────── #
const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

.cap-page {
  font-family: 'Inter', sans-serif;
  background: #080b14;
  min-height: 100vh;
  color: #e5e7eb;
  padding: 28px 32px;
  box-sizing: border-box;
}

.cap-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 28px;
}

.cap-breadcrumb {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 6px;
  display: flex;
  gap: 6px;
  align-items: center;
}
.cap-breadcrumb-link { color: #6366f1; text-decoration: none; }
.cap-breadcrumb-link:hover { text-decoration: underline; }
.cap-breadcrumb-sep { color: #374151; }

.cap-title {
  font-size: 26px;
  font-weight: 800;
  background: linear-gradient(135deg, #818cf8, #38bdf8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0 0 4px;
}
.cap-subtitle { font-size: 13px; color: #6b7280; margin: 0; }

.cap-btn-refresh {
  padding: 9px 18px;
  border-radius: 8px;
  border: 1px solid rgba(99,102,241,0.4);
  background: rgba(99,102,241,0.1);
  color: #818cf8;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 13px;
}
.cap-btn-refresh:hover:not(:disabled) {
  background: rgba(99,102,241,0.2);
  border-color: #818cf8;
}
.cap-btn-refresh:disabled { opacity: 0.5; cursor: not-allowed; }

.cap-kpi-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 14px;
  margin-bottom: 22px;
}
.cap-kpi-card {
  background: linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 12px;
  padding: 18px 20px;
  text-align: center;
  transition: transform 0.2s;
}
.cap-kpi-card:hover { transform: translateY(-2px); }
.cap-kpi-value { font-size: 28px; font-weight: 800; margin-bottom: 4px; }
.cap-kpi-label { font-size: 11px; color: #6b7280; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }

.cap-datebar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}
.cap-preset {
  padding: 6px 14px;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(255,255,255,0.04);
  color: #9ca3af;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.cap-preset:hover { background: rgba(99,102,241,0.1); border-color: rgba(99,102,241,0.4); color: #818cf8; }
.cap-preset--active { background: rgba(99,102,241,0.15); border-color: #6366f1; color: #818cf8; font-weight: 600; }
.cap-input {
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(255,255,255,0.04);
  color: #e5e7eb;
  font-size: 12px;
  outline: none;
}
.cap-input:focus { border-color: #6366f1; }

.cap-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  border-bottom: 1px solid rgba(255,255,255,0.07);
  padding-bottom: 0;
}
.cap-tab {
  padding: 10px 18px;
  border: none;
  background: transparent;
  color: #6b7280;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.15s;
  margin-bottom: -1px;
}
.cap-tab:hover { color: #9ca3af; }
.cap-tab--active { color: #818cf8; border-bottom-color: #6366f1; font-weight: 600; }

.cap-panel {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px;
  padding: 24px;
  min-height: 300px;
}
.cap-panel-legend {
  display: flex;
  align-items: center;
  font-size: 11px;
  color: #6b7280;
  margin-bottom: 20px;
}
.cap-legend-dot {
  display: inline-block;
  width: 10px; height: 10px;
  border-radius: 50%;
  margin-right: 6px;
}

.cap-loading, .cap-empty {
  text-align: center;
  padding: 48px;
  color: #6b7280;
  font-size: 14px;
}
.cap-empty--good { color: #22c55e; }
.cap-error {
  background: rgba(239,68,68,0.1);
  border: 1px solid rgba(239,68,68,0.3);
  border-radius: 8px;
  padding: 12px 16px;
  color: #fca5a5;
  margin-bottom: 16px;
  font-size: 13px;
}

/* Load bar */
.cap-load-list { display: flex; flex-direction: column; gap: 14px; }
.cap-load-row {
  display: grid;
  grid-template-columns: 200px 1fr 120px 80px;
  align-items: center;
  gap: 16px;
}
.cap-load-label { display: flex; flex-direction: column; gap: 2px; }
.cap-ws-code { font-size: 12px; font-weight: 700; color: #e5e7eb; font-family: monospace; }
.cap-ws-name { font-size: 11px; color: #6b7280; }

.cap-bar-wrap {
  position: relative;
  height: 18px;
  background: rgba(255,255,255,0.06);
  border-radius: 9px;
  overflow: visible;
}
.cap-bar-fill {
  height: 100%;
  border-radius: 9px;
  transition: width 0.6s cubic-bezier(.4,0,.2,1);
  min-width: 4px;
  max-width: 100%;
}
.cap-marker {
  position: absolute;
  top: -4px;
  bottom: -4px;
  width: 1px;
  background: rgba(255,255,255,0.15);
}
.cap-marker--70 { left: calc(70% / 1.2); }
.cap-marker--90 { left: calc(90% / 1.2); }
.cap-marker--100 { left: calc(100% / 1.2); background: rgba(255,255,255,0.3); }

.cap-load-stats { display: flex; flex-direction: column; gap: 2px; align-items: flex-end; }

.cap-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-align: center;
}
.cap-badge--ok { background: rgba(34,197,94,0.15); color: #22c55e; }
.cap-badge--warning { background: rgba(245,158,11,0.15); color: #f59e0b; }
.cap-badge--critical { background: rgba(239,68,68,0.15); color: #ef4444; }

/* Bottleneck cards */
.cap-alerts-list { display: flex; flex-direction: column; gap: 14px; }
.cap-alert-card {
  border-radius: 12px;
  padding: 18px 20px;
  border: 1px solid;
}
.cap-alert-card--warning {
  background: rgba(245,158,11,0.07);
  border-color: rgba(245,158,11,0.25);
}
.cap-alert-card--critical {
  background: rgba(239,68,68,0.07);
  border-color: rgba(239,68,68,0.25);
}
.cap-alert-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.cap-alert-icon { font-size: 18px; }
.cap-alert-title { font-weight: 700; font-size: 15px; color: #e5e7eb; flex: 1; }
.cap-alert-pct { font-weight: 700; font-size: 14px; }
.cap-alert-suggestion { color: #9ca3af; font-size: 13px; margin: 0 0 8px; }
.cap-alert-overtime {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 6px;
  background: rgba(239,68,68,0.1);
  color: #fca5a5;
  font-size: 12px;
}
`
