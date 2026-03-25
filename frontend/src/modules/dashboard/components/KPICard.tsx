import { Link } from "react-router-dom"
import { KPIData } from "@/types/inventory.types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ArrowDownIcon, ArrowRightIcon, ArrowUpIcon, PackageOpen } from "lucide-react"
import { cn } from "@/lib/utils"

interface KPICardProps {
  data: KPIData
  href?: string
}

export function KPICard({ data, href }: KPICardProps) {
  const content = (
    <Card className={cn(href && "cursor-pointer hover:shadow-md hover:border-primary/40 transition-all")}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{data.label}</CardTitle>
        <PackageOpen className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{data.value}</div>
        <p className="text-xs text-muted-foreground flex items-center mt-1">
          {data.trend === "up" && <ArrowUpIcon className="mr-1 h-3 w-3 text-emerald-500" />}
          {data.trend === "down" && <ArrowDownIcon className="mr-1 h-3 w-3 text-destructive" />}
          {data.trend === "neutral" && <ArrowRightIcon className="mr-1 h-3 w-3 text-muted-foreground" />}
          <span
            className={
              data.trend === "down" && data.label.includes("Alerts") ? "text-destructive font-medium" :
              data.trend === "up" && !data.label.includes("Alerts") ? "text-emerald-500 font-medium" : ""
            }
          >
            {data.change > 0 ? "+" : ""}{data.change}
          </span>
          <span className="ml-1 text-muted-foreground">from last month</span>
        </p>
      </CardContent>
    </Card>
  )

  if (href) {
    return <Link to={href} className="block">{content}</Link>
  }

  return content
}
