import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ReactNode, useState } from "react"

export function QueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000, // 5 minutes
            retry: 1, // Retry failed requests once (good for brief offline)
            refetchOnWindowFocus: false, // Prevent unnecessary fetches
            // Handle errors gracefully
            throwOnError: false, // Don't throw errors, let components handle them
            gcTime: 10 * 60 * 1000, // Garbage collect after 10 minutes
          },
          mutations: {
            retry: 1,
            throwOnError: false, // Handle mutation errors in components
          },
        },
      })
  )

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}
