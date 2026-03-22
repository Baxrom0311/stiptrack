"use client"

import { useEffect } from "react"

import ErrorState from "@/components/ui/error-state"

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-100 antialiased">
        <ErrorState
          title="Sahifani yuklashda xatolik yuz berdi"
          description="Kutilmagan frontend xatosi yuz berdi. Qayta urinib ko‘ring, muammo saqlansa sahifani yangilang."
          onRetry={reset}
          backHref="/"
        />
      </body>
    </html>
  )
}
