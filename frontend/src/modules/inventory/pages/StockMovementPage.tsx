import { PageHeader } from "@/components/layout/PageHeader"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ArrowDownToLine, ArrowUpToLine, ArrowRightLeft } from "lucide-react"

export default function StockMovementPage() {
  return (
    <div className="max-w-4xl space-y-6">
      <PageHeader 
        title="Stock Movements" 
        description="Receive, issue, or transfer inventory items."
      />

      <Tabs defaultValue="receive" className="w-full">
        <TabsList className="grid w-full grid-cols-3 max-w-md mb-8">
          <TabsTrigger value="receive" className="data-[state=active]:bg-emerald-500/10 data-[state=active]:text-emerald-700 dark:data-[state=active]:text-emerald-400">
            <ArrowDownToLine className="w-4 h-4 mr-2" />
            Receive
          </TabsTrigger>
          <TabsTrigger value="issue" className="data-[state=active]:bg-amber-500/10 data-[state=active]:text-amber-700 dark:data-[state=active]:text-amber-400">
            <ArrowUpToLine className="w-4 h-4 mr-2" />
            Issue
          </TabsTrigger>
          <TabsTrigger value="transfer" className="data-[state=active]:bg-blue-500/10 data-[state=active]:text-blue-700 dark:data-[state=active]:text-blue-400">
            <ArrowRightLeft className="w-4 h-4 mr-2" />
            Transfer
          </TabsTrigger>
        </TabsList>

        <TabsContent value="receive">
          <Card>
            <CardHeader>
              <CardTitle>Receive Goods</CardTitle>
              <CardDescription>Add new stock into the warehouse. Generates a new batch if applicable.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>Product ID / Barcode</Label>
                  <Input placeholder="Scan or type..." />
                </div>
                <div className="space-y-2">
                  <Label>Quantity to Receive</Label>
                  <Input type="number" placeholder="0" />
                </div>
                <div className="space-y-2">
                  <Label>Batch Number (Optional)</Label>
                  <Input placeholder="LOT-..." />
                </div>
                <div className="space-y-2">
                  <Label>Location / Bin</Label>
                  <Select>
                    <SelectTrigger><SelectValue placeholder="Select Bin" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="A1">Warehouse A - Bin 1</SelectItem>
                      <SelectItem value="A2">Warehouse A - Bin 2</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <Button className="w-full sm:w-auto mt-4">Confirm Receipt</Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="issue">
          <Card>
            <CardHeader>
              <CardTitle>Issue Materials</CardTitle>
              <CardDescription>Consume parts for manufacturing or manual dispatch.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>Product ID / Barcode</Label>
                  <Input placeholder="Scan or type..." />
                </div>
                <div className="space-y-2">
                  <Label>Quantity to Issue</Label>
                  <Input type="number" placeholder="0" />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label>Reference (Work Order / Reason)</Label>
                  <Input placeholder="WO-..." />
                </div>
              </div>
              <Button className="w-full sm:w-auto mt-4" variant="secondary">Confirm Issue</Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="transfer">
           <Card>
            <CardHeader>
              <CardTitle>Transfer Stock</CardTitle>
              <CardDescription>Move inventory between locations.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                  <Label>Product ID / Barcode</Label>
                  <Input placeholder="Scan or type..." />
              </div>
              <div className="grid gap-4 sm:grid-cols-2 grid-rows-2">
                <div className="space-y-2">
                  <Label>From Location</Label>
                  <Select>
                    <SelectTrigger><SelectValue placeholder="Select Source" /></SelectTrigger>
                    <SelectContent><SelectItem value="A1">A1</SelectItem></SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>To Location</Label>
                  <Select>
                    <SelectTrigger><SelectValue placeholder="Select Destination" /></SelectTrigger>
                    <SelectContent><SelectItem value="B1">B1</SelectItem></SelectContent>
                  </Select>
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label>Quantity</Label>
                  <Input type="number" placeholder="0" />
                </div>
              </div>
              <Button className="w-full sm:w-auto mt-4">Execute Transfer</Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
