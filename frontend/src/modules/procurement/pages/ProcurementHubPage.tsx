import { Link } from "react-router-dom"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Truck, ClipboardCheck, Building2 } from "lucide-react"

const links = [
  { to: "/procurement/suppliers", title: "Suppliers", desc: "Vendor master & edit", icon: Building2 },
  { to: "/procurement/purchase-orders", title: "Purchase orders", desc: "Create, send, acknowledge", icon: Truck },
  { to: "/procurement/grn", title: "Goods receipt (GRN)", desc: "Receive against PO", icon: ClipboardCheck },
]

export default function ProcurementHubPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Procurement</h1>
        <p className="text-muted-foreground">End-to-end supply chain: suppliers → PO → GRN → inventory</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {links.map((l) => (
          <Link key={l.to} to={l.to}>
            <Card className="h-full transition-colors hover:bg-accent/50">
              <CardHeader className="flex flex-row items-center gap-2 space-y-0">
                <l.icon className="h-5 w-5 text-primary" />
                <CardTitle className="text-base">{l.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription>{l.desc}</CardDescription>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}
