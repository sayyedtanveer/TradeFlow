import { ReactNode } from 'react'
import { ChevronRight } from 'lucide-react'

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
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center rounded-lg bg-gray-50 px-4 py-12 text-center">
        <p className="text-gray-600">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className={className}>
      {/* Mobile View - Cards */}
      <div className="space-y-3 md:hidden">
        {data.map((item, idx) => (
          <MobileTableCard
            key={idx}
            item={item}
            columns={columns}
            onClick={() => onRowClick?.(item)}
          />
        ))}
      </div>

      {/* Desktop View - Table */}
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="px-6 py-3 text-left font-semibold text-gray-900"
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((item, idx) => (
              <tr
                key={idx}
                className="cursor-pointer border-b border-gray-100 transition-colors hover:bg-gray-50"
                onClick={() => onRowClick?.(item)}
              >
                {columns.map((col) => (
                  <td key={col.key} className="px-6 py-4 text-gray-700">
                    {col.render ? col.render(item[col.key], item) : item[col.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/**
 * MobileTableCard - Individual card for mobile view
 */
interface MobileTableCardProps {
  item: any
  columns: MobileTableColumn[]
  onClick?: () => void
}

const MobileTableCard = ({ item, columns, onClick }: MobileTableCardProps) => {
  return (
    <div
      onClick={onClick}
      className="cursor-pointer rounded-lg border border-gray-200 bg-white p-4 shadow-sm transition-all hover:shadow-md active:bg-gray-50"
    >
      <div className="space-y-3">
        {columns.map((col) => (
          <div key={col.key} className="flex items-start justify-between gap-3">
            <span className="text-xs font-medium text-gray-600">{col.label}</span>
            <span className="text-right text-sm text-gray-900">
              {col.render ? col.render(item[col.key], item) : item[col.key]}
            </span>
          </div>
        ))}
      </div>

      {/* Click indicator */}
      <div className="mt-4 flex items-center justify-end">
        <ChevronRight className="h-4 w-4 text-gray-400" />
      </div>
    </div>
  )
}

export default MobileTable
