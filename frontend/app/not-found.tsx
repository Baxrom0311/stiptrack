import ErrorState from "@/components/ui/error-state"

export default function NotFoundPage() {
  return (
    <ErrorState
      title="Sahifa topilmadi"
      description="So‘ralgan manzil mavjud emas yoki ko‘chirilgan. Menyudan kerakli bo‘limga qayting."
      backHref="/login"
      backLabel="Login sahifasi"
    />
  )
}
