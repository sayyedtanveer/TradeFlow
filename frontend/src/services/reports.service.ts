import { DashboardReport } from "@/types/inventory.types"

// Temporary mock data until reports backend endpoints are fully built
const mockDashboardData: DashboardReport = {
  kpis: [
    { label: "Total Products", value: 1248, change: 12, trend: "up" },
    { label: "Low Stock Alerts", value: 23, change: -5, trend: "down" },
    { label: "Open Work Orders", value: 45, change: 8, trend: "up" },
    { label: "Pending Shipments", value: 12, change: 0, trend: "neutral" }
  ],
  recentActivities: [
    { id: "1", type: "movement", description: "Added 500 units of Raw Material A", timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(), user: "John Doe" },
    { id: "2", type: "alert", description: "SKU-992 fell below reorder point", timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(), user: "System" },
    { id: "3", type: "system", description: "Monthly inventory report generated", timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(), user: "System" },
    { id: "4", type: "movement", description: "Transferred 100 units to Line 1", timestamp: new Date(Date.now() - 1000 * 60 * 60 * 25).toISOString(), user: "Jane Smith" },
  ]
}

export const reportsService = {
  async getDashboard(): Promise<DashboardReport> {
    try {
      // In production, replacing with actual API call:
      // const response = await apiClient.get<DashboardReport>("/reports/dashboard")
      // return response.data
      
      // Simulating network delay
      await new Promise(resolve => setTimeout(resolve, 600))
      return mockDashboardData
    } catch (e) {
      throw e
    }
  }
}
