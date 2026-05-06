import { ReactNode } from 'react'
import ResponsiveDataList from "@/components/shared/ResponsiveDataList"

export interface MobileTableColumn {
  key: string
  label: string
  render?: (value: any, item: any) => ReactNode
}

export interface MobileTableProps {
  columns: MobileTableColumn[]
  data: any[]
  onRowClick?: (item: any) => void
  className?: string
  emptyMessage?: string
}

/**
 * MobileTable Component
 * Responsive table that shows cards on mobile, table on desktop
 */
export const MobileTable = ({
  columns,
  data,
  onRowClick,
  className = '',
  emptyMessage = 'No data available',
}: MobileTableProps) => {
  return (
    <ResponsiveDataList
      className={className}
      data={data}
      columns={columns.map((col) => ({
        key: col.key,
        header: col.label,
        cell: (item) => {
          const record = item as Record<string, any>
          return col.render ? col.render(record[col.key], record) : record[col.key]
        },
      }))}
      getRowKey={(item, idx) => {
        const record = (item ?? {}) as Record<string, any>
        return String(record.id ?? record.key ?? idx)
      }}
      onRowClick={onRowClick}
      emptyState={emptyMessage}
      renderMobileCard={(item) => (
        <div
          onClick={() => onRowClick?.(item)}
          className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition-all hover:shadow-md"
        >
          <div className="space-y-3">
            {columns.map((col) => (
              <div key={col.key} className="flex items-start justify-between gap-3">
                <span className="text-xs font-medium uppercase tracking-[0.14em] text-slate-500">{col.label}</span>
                <span className="text-right text-sm text-slate-900">
                  {(() => {
                    const record = item as Record<string, any>
                    return col.render ? col.render(record[col.key], record) : record[col.key]
                  })()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    />
  )
}

export default MobileTable
