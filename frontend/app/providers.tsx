"use client"

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useEffect, useRef, useState, type ReactNode } from "react"
import { Toaster } from "sonner"

import { clearAuthSession } from "@/lib/auth-session"
import { notifyWarning } from "@/lib/notifications"
import { useAuthStore } from "@/store/authStore"

export default function Providers({ children }: { children: ReactNode }) {
  const clearAuthStore = useAuthStore((state) => state.logout)
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
            staleTime: 30_000,
            retry: 1,
          },
        },
      }),
  )
  const authWarningTimeoutRef = useRef<number | null>(null)

  useEffect(() => {
    if (typeof window === "undefined") {
      return
    }

    const handleUnauthorized = () => {
      clearAuthStore()
      clearAuthSession()
      queryClient.clear()
      if (authWarningTimeoutRef.current !== null) {
        return
      }

      notifyWarning("Sessiya tugadi. Qayta kiring.")
      authWarningTimeoutRef.current = window.setTimeout(() => {
        authWarningTimeoutRef.current = null
      }, 3000)
    }

    window.addEventListener("auth:unauthorized", handleUnauthorized)

    return () => {
      window.removeEventListener("auth:unauthorized", handleUnauthorized)
      if (authWarningTimeoutRef.current !== null) {
        window.clearTimeout(authWarningTimeoutRef.current)
      }
    }
  }, [clearAuthStore, queryClient])

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster position="top-right" richColors closeButton duration={3500} />
    </QueryClientProvider>
  )
}
