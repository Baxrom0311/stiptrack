"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useMutation } from "@tanstack/react-query"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useAuth } from "@/hooks/useAuth"
import { FieldErrors, getFieldErrors, getFirstFieldError, loginFormSchema } from "@/lib/form-validation"
import { extractErrorMessage, notifyError, notifySuccess } from "@/lib/notifications"

type LoginFormState = {
  email: string
  password: string
}

const EMPTY_FORM: LoginFormState = {
  email: "",
  password: "",
}

export default function LoginPage() {
  const router = useRouter()
  const auth = useAuth()
  const [form, setForm] = useState<LoginFormState>(EMPTY_FORM)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors<keyof LoginFormState>>({})
  const [formError, setFormError] = useState<string | null>(null)

  const loginMutation = useMutation({
    mutationFn: async () => {
      const parsed = loginFormSchema.safeParse(form)
      if (!parsed.success) {
        const errors = getFieldErrors<keyof LoginFormState>(parsed.error)
        setFieldErrors(errors)
        throw new Error(getFirstFieldError(errors) ?? "Formada xatolik bor.")
      }

      setFieldErrors({})
      setFormError(null)

      const result = await auth.login(parsed.data)
      return result.user.role
    },
    onSuccess: (role) => {
      notifySuccess("Tizimga muvaffaqiyatli kirildi.")
      router.push(`/${role}/dashboard`)
    },
    onError: (error) => {
      const message = extractErrorMessage(error)
      setFormError(message)
      notifyError(message)
    },
  })

  return (
    <main className="mx-auto flex min-h-screen max-w-md items-center px-4 py-8">
      <Card className="w-full border-slate-200">
        <CardHeader className="space-y-2">
          <CardTitle>Login</CardTitle>
          <CardDescription>Email va parol orqali tizimga kiring.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="login-email">
              Email
            </label>
            <Input
              id="login-email"
              type="email"
              value={form.email}
              aria-invalid={Boolean(fieldErrors.email)}
              onChange={(event) => {
                setForm((prev) => ({ ...prev, email: event.target.value }))
                setFieldErrors((prev) => ({ ...prev, email: undefined }))
                setFormError(null)
              }}
              placeholder="student@university.uz"
            />
            {fieldErrors.email && <p className="mt-1 text-xs text-red-600">{fieldErrors.email}</p>}
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="login-password">
              Parol
            </label>
            <Input
              id="login-password"
              type="password"
              value={form.password}
              aria-invalid={Boolean(fieldErrors.password)}
              onChange={(event) => {
                setForm((prev) => ({ ...prev, password: event.target.value }))
                setFieldErrors((prev) => ({ ...prev, password: undefined }))
                setFormError(null)
              }}
              placeholder="Kamida 8 ta belgi"
            />
            {fieldErrors.password && <p className="mt-1 text-xs text-red-600">{fieldErrors.password}</p>}
          </div>

          {formError && <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{formError}</div>}

          <Button type="button" className="w-full" onClick={() => loginMutation.mutate()} disabled={loginMutation.isPending}>
            {loginMutation.isPending ? "Kirilmoqda..." : "Kirish"}
          </Button>

          <p className="text-center text-sm text-slate-600">
            Akkount yo‘qmi?{" "}
            <Link href="/register" className="font-medium text-slate-900 underline">
              Ro‘yxatdan o‘tish
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  )
}
