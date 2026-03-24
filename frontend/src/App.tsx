import { RouterProvider } from "react-router-dom"
import { router } from "@/app/routes"
import { QueryProvider } from "@/app/providers/QueryProvider"
import { Toaster } from "@/components/ui/toaster"

export default function App() {
  return (
    <QueryProvider>
      <RouterProvider router={router} />
      <Toaster />
    </QueryProvider>
  )
}
