import type { ReactNode } from "react"
import { Link, useLocation } from "react-router-dom"
import {
  ArrowLeft,
  BadgeDollarSign,
  ClipboardList,
  FileSpreadsheet,
  HandCoins,
  type LucideIcon,
  ReceiptText,
  ScrollText,
  TriangleAlert,
  UserRound,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type SupplierPortalTabKey =
  | "purchaseOrders"
  | "quotations"
  | "receipts"
  | "invoices"
  | "payments"
  | "profile"

type SupplierPortalCountMap = Partial<Record<SupplierPortalTabKey, number>>

type SupplierPortalTab = {
  key: SupplierPortalTabKey
  label: string
  href: string
  icon: LucideIcon
}

const supplierPortalTabs: SupplierPortalTab[] = [
  { key: "purchaseOrders", label: "POs", href: "/supplier-portal", icon: ClipboardList },
  { key: "quotations", label: "Quotations", href: "/supplier-portal/quotations", icon: FileSpreadsheet },
  { key: "receipts", label: "Receipts", href: "/supplier-portal/receipts", icon: ReceiptText },
  { key: "invoices", label: "Invoices", href: "/supplier-portal/invoices", icon: ScrollText },
  { key: "payments", label: "Payments", href: "/supplier-portal/payments", icon: HandCoins },
  { key: "profile", label: "Profile", href: "/supplier-portal/profile", icon: UserRound },
]

const normalizePath = (path: string) => path.replace(/\/+$/, "") || "/"

const isActivePath = (pathname: string, href: string) => {
  const cleanPath = normalizePath(pathname)
  const cleanHref = normalizePath(href)

  if (cleanHref === "/supplier-portal") {
    return cleanPath === cleanHref || cleanPath.startsWith(`${cleanHref}/po/`)
  }

  return cleanPath === cleanHref || cleanPath.startsWith(`${cleanHref}/`)
}

export function SupplierPortalTabs({ counts }: { counts?: SupplierPortalCountMap }) {
  const location = useLocation()

  return (
    <nav className="erp-portal-tabs-scroll -mx-1 w-full max-w-full min-w-0 overflow-x-auto px-1 pb-1 erp-dark-scrollbar" aria-label="Supplier portal workspaces">
      <div className="flex w-max min-w-full snap-x gap-2">
        {supplierPortalTabs.map((tab) => {
          const isActive = isActivePath(location.pathname, tab.href)
          const Icon = tab.icon
          const count = counts?.[tab.key]

          return (
            <Link
              key={tab.href}
              to={tab.href}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "erp-portal-tab group min-w-max snap-start",
                isActive && "erp-portal-tab-active"
              )}
            >
              <span
                className={cn(
                  "rounded-full p-2 transition-colors",
                  isActive ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-500 group-hover:bg-slate-200"
                )}
              >
                <Icon className="h-4 w-4" />
              </span>
              <span className="font-medium">{tab.label}</span>
              {typeof count === "number" && (
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-[11px] font-semibold",
                    isActive ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-600"
                  )}
                >
                  {count}
                </span>
              )}
            </Link>
          )
        })}
      </div>
    </nav>
  )
}

export function SupplierPortalHeader({
  eyebrow,
  title,
  description,
  backHref,
  backLabel,
  actions,
}: {
  eyebrow?: string
  title: string
  description: string
  backHref?: string
  backLabel?: string
  actions?: ReactNode
}) {
  return (
    <header className="erp-portal-section erp-subtle-grid w-full max-w-full min-w-0 overflow-hidden p-4 sm:p-5">
      <div className="flex w-full min-w-0 flex-col gap-4 2xl:flex-row 2xl:items-center 2xl:justify-between">
        <div className="min-w-0 space-y-2">
          {backHref && backLabel && (
            <Button variant="ghost" size="sm" asChild className="-ml-2 w-fit text-slate-500 hover:text-slate-900">
              <Link to={backHref}>
                <ArrowLeft className="h-4 w-4" />
                {backLabel}
              </Link>
            </Button>
          )}
          {eyebrow && (
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-blue-600">{eyebrow}</p>
          )}
          <div className="space-y-2">
            <h1 className="break-words text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">{title}</h1>
            <p className="max-w-2xl break-words text-sm leading-6 text-slate-600 sm:text-base">{description}</p>
          </div>
        </div>
        {actions ? <div className="flex w-full min-w-0 flex-col gap-3 2xl:w-auto 2xl:flex-row 2xl:items-start">{actions}</div> : null}
      </div>
    </header>
  )
}

export function SupplierPortalKpiCard({
  label,
  value,
  helper,
  icon: Icon,
  tone = "blue",
}: {
  label: string
  value: ReactNode
  helper?: string
  icon: LucideIcon
  tone?: "blue" | "green" | "amber" | "slate"
}) {
  const toneStyles = {
    blue: {
      card: "from-blue-50/80 via-white to-sky-50/80 before:bg-blue-500",
      icon: "border-blue-100 bg-blue-50 text-blue-600",
    },
    green: {
      card: "from-emerald-50/80 via-white to-teal-50/80 before:bg-emerald-500",
      icon: "border-emerald-100 bg-emerald-50 text-emerald-600",
    },
    amber: {
      card: "from-amber-50/90 via-white to-orange-50/80 before:bg-amber-500",
      icon: "border-amber-100 bg-amber-50 text-amber-600",
    },
    slate: {
      card: "from-slate-100/80 via-white to-blue-50/70 before:bg-slate-700",
      icon: "border-slate-200 bg-slate-100 text-slate-700",
    },
  } satisfies Record<typeof tone, { card: string; icon: string }>

  return (
    <article className={cn("erp-portal-kpi-card", toneStyles[tone].card)}>
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">{label}</p>
          <div className="text-4xl font-semibold tracking-tight text-slate-950">{value}</div>
          {helper ? <p className="text-sm text-slate-600">{helper}</p> : null}
        </div>
        <div className={cn("rounded-2xl border p-3 shadow-sm", toneStyles[tone].icon)}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </article>
  )
}

export function SupplierPortalAlertBanner({
  tone = "warning",
  title,
  description,
}: {
  tone?: "warning" | "critical"
  title: string
  description: string
}) {
  return (
    <div className={cn("erp-portal-banner", tone === "critical" ? "erp-portal-banner-critical" : "erp-portal-banner-warning")}>
      <div className="rounded-full p-2">
        <TriangleAlert className="h-4 w-4" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-semibold">{title}</p>
        <p className="text-sm opacity-90">{description}</p>
      </div>
    </div>
  )
}

export function SupplierPortalStatusBadge({ status }: { status: string }) {
  const value = status.trim().toLowerCase()

  if (["received", "paid", "accepted", "submitted", "completed", "closed"].includes(value)) {
    return <Badge className="border-green-200 bg-green-50 text-green-700 hover:bg-green-100">{status}</Badge>
  }

  if (["overdue", "rejected", "cancelled"].includes(value)) {
    return <Badge className="border-red-200 bg-red-50 text-red-700 hover:bg-red-100">{status}</Badge>
  }

  if (["draft", "partial", "pending"].includes(value)) {
    return <Badge className="border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100">{status}</Badge>
  }

  return <Badge className="border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100">{status}</Badge>
}

export function SupplierPortalEmptyState({
  title,
  description,
  actionHref,
  actionLabel,
}: {
  title: string
  description: string
  actionHref?: string
  actionLabel?: string
}) {
  return (
    <div className="rounded-[28px] border border-dashed border-slate-300 bg-slate-50 p-8 text-center shadow-sm">
      <div className="mx-auto flex max-w-md flex-col items-center gap-3">
        <div className="rounded-full bg-white p-3 text-slate-400 shadow-sm">
          <BadgeDollarSign className="h-5 w-5" />
        </div>
        <div className="space-y-2">
          <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
          <p className="text-sm leading-6 text-slate-600">{description}</p>
        </div>
        {actionHref && actionLabel ? (
          <Button asChild variant="outline" className="mt-2">
            <Link to={actionHref}>{actionLabel}</Link>
          </Button>
        ) : null}
      </div>
    </div>
  )
}
