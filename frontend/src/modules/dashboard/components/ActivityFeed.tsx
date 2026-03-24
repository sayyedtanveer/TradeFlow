import { ActivityItem } from "@/types/inventory.types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatDistanceToNow } from "date-fns"
import { AlertCircle, ArrowRightLeft, Settings } from "lucide-react"

interface ActivityFeedProps {
  activities: ActivityItem[]
}

const getIcon = (type: string) => {
  switch (type) {
    case "movement": return <ArrowRightLeft className="h-4 w-4 text-primary" />
    case "alert": return <AlertCircle className="h-4 w-4 text-destructive" />
    case "system": return <Settings className="h-4 w-4 text-muted-foreground" />
    default: return <Settings className="h-4 w-4" />
  }
}

export function ActivityFeed({ activities }: ActivityFeedProps) {
  return (
    <Card className="col-span-1 border md:col-span-3">
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-8">
          {activities.length === 0 ? (
            <p className="text-sm text-muted-foreground">No recent activity.</p>
          ) : (
            activities.map((activity) => (
              <div key={activity.id} className="flex items-center">
                <div className="space-y-1">
                  <p className="text-sm font-medium leading-none flex items-center gap-2">
                    {getIcon(activity.type)}
                    {activity.description}
                  </p>
                  <p className="text-xs text-muted-foreground pl-6">
                    {activity.user && `${activity.user} • `} 
                    {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  )
}
