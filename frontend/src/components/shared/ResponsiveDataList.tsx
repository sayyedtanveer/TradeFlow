import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

export type ResponsiveDataColumn<T> = {
  key: string
  header: ReactNode
  cell: (item: T) => ReactNode
  className?: string
  headerClassName?: string
}

interface ResponsiveDataListProps<T> {
  data: T[]
  columns: ResponsiveDataColumn<T>[]
  getRowKey: (item: T, index: number) => string
  renderMobileCard: (item: T, index: number) => ReactNode
  emptyState?: ReactNode
  onRowClick?: (item: T) => void
  className?: string
  tableWrapperClassName?: string
  tableClassName?: string
  mobileListClassName?: string
}

export function ResponsiveDataList<T>({
  data,
  columns,
  getRowKey,
  renderMobileCard,
  emptyState,
  onRowClick,
  className,
  tableWrapperClassName,
  tableClassName,
  mobileListClassName,
}: ResponsiveDataListProps<T>) {
  if (!data.length) {
    if (emptyState != null && typeof emptyState !== "string" && typeof emptyState !== "number") {
      return <div className={cn("w-full", className)}>{emptyState}</div>
    }

    return (
      <div className={cn("rounded-3xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-500", className)}>
        {emptyState ?? "No records found."}
      </div>
    )
  }

  return (
    <div className={cn("w-full", className)}>
      <div className={cn("space-y-4 md:hidden", mobileListClassName)}>
        {data.map((item, index) => (
          <div key={getRowKey(item, index)}>{renderMobileCard(item, index)}</div>
        ))}
      </div>

      <div className={cn("hidden overflow-x-auto rounded-3xl border border-slate-200/80 bg-white shadow-sm md:block", tableWrapperClassName)}>
        <table className={cn("w-full min-w-[720px] text-sm", tableClassName)}>
          <thead className="bg-slate-50/90 text-left text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            <tr>
              {columns.map((column) => (
                <th key={column.key} className={cn("px-4 py-3", column.headerClassName)}>
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.map((item, index) => {
              const key = getRowKey(item, index)
              return (
                <tr
                  key={key}
                  className={cn(
                    "transition-colors odd:bg-white even:bg-slate-50/50 hover:bg-blue-50/40",
                    onRowClick && "cursor-pointer"
                  )}
                  onClick={onRowClick ? () => onRowClick(item) : undefined}
                >
                  {columns.map((column) => (
                    <td key={`${key}-${column.key}`} className={cn("px-4 py-3 align-middle text-slate-700", column.className)}>
                      {column.cell(item)}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default ResponsiveDataList
