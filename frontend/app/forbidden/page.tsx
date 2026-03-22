import ErrorState from "@/components/ui/error-state"

export default function ForbiddenPage() {
  return (
    <ErrorState
      title="Ruxsat yo‘q"
      description="Bu bo‘lim sizning rol’ingiz uchun ochiq emas. To‘g‘ri panelga kiring yoki administrator bilan bog‘laning."
      backHref="/login"
      backLabel="Qayta kirish"
    />
  )
}
