"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useMutation } from "@tanstack/react-query"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useAuth } from "@/hooks/useAuth"
import { FieldErrors, getFieldErrors, getFirstFieldError, registerFormSchema } from "@/lib/form-validation"
import { extractErrorMessage, notifyError, notifySuccess } from "@/lib/notifications"

type RegisterFormState = {
  full_name: string
  email: string
  password: string
  confirm_password: string
  department: string
  student_id: string
}

const EMPTY_FORM: RegisterFormState = {
  full_name: "",
  email: "",
  password: "",
  confirm_password: "",
  department: "",
  student_id: "",
}

export default function RegisterPage() {
  const router = useRouter()
  const auth = useAuth()
  const [form, setForm] = useState<RegisterFormState>(EMPTY_FORM)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors<keyof RegisterFormState>>({})
  const [formError, setFormError] = useState<string | null>(null)

  const registerMutation = useMutation({
    mutationFn: async () => {
      const parsed = registerFormSchema.safeParse(form)
      if (!parsed.success) {
        const errors = getFieldErrors<keyof RegisterFormState>(parsed.error)
        setFieldErrors(errors)
        throw new Error(getFirstFieldError(errors) ?? "Formada xatolik bor.")
      }

      setFieldErrors({})
      setFormError(null)

      return auth.register({
        full_name: parsed.data.full_name,
        email: parsed.data.email,
        password: parsed.data.password,
        department: parsed.data.department || null,
        student_id: parsed.data.student_id || null,
        is_supervisor: false,
      })
    },
    onSuccess: () => {
      notifySuccess("Ro‘yxatdan o‘tish muvaffaqiyatli tugadi. Endi login qiling.")
      router.push("/login")
    },
    onError: (error) => {
      const message = extractErrorMessage(error)
      setFormError(message)
      notifyError(message)
    },
  })

  const setFieldValue = <K extends keyof RegisterFormState>(field: K, value: RegisterFormState[K]) => {
    setForm((prev) => ({ ...prev, [field]: value }))
    setFieldErrors((prev) => ({ ...prev, [field]: undefined }))
    setFormError(null)
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-xl items-center px-4 py-8">
      <Card className="w-full border-slate-200">
        <CardHeader className="space-y-2">
          <CardTitle>Register</CardTitle>
          <CardDescription>Student akkaunti uchun asosiy ma’lumotlarni kiriting.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="register-full-name">
              F.I.Sh
            </label>
            <Input
              id="register-full-name"
              value={form.full_name}
              aria-invalid={Boolean(fieldErrors.full_name)}
              onChange={(event) => setFieldValue("full_name", event.target.value)}
              placeholder="Ism Familiya"
            />
            {fieldErrors.full_name && <p className="mt-1 text-xs text-red-600">{fieldErrors.full_name}</p>}
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="register-email">
                Email
              </label>
              <Input
                id="register-email"
                type="email"
                value={form.email}
                aria-invalid={Boolean(fieldErrors.email)}
                onChange={(event) => setFieldValue("email", event.target.value)}
                placeholder="student@university.uz"
              />
              {fieldErrors.email && <p className="mt-1 text-xs text-red-600">{fieldErrors.email}</p>}
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="register-student-id">
                Student ID
              </label>
              <Input
                id="register-student-id"
                value={form.student_id}
                aria-invalid={Boolean(fieldErrors.student_id)}
                onChange={(event) => setFieldValue("student_id", event.target.value)}
                placeholder="Masalan: 220145"
              />
              {fieldErrors.student_id && <p className="mt-1 text-xs text-red-600">{fieldErrors.student_id}</p>}
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="register-department">
              Fakultet/Bo‘lim
            </label>
            <Input
              id="register-department"
              value={form.department}
              aria-invalid={Boolean(fieldErrors.department)}
              onChange={(event) => setFieldValue("department", event.target.value)}
              placeholder="Masalan: Kompyuter injiniring"
            />
            {fieldErrors.department && <p className="mt-1 text-xs text-red-600">{fieldErrors.department}</p>}
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="register-password">
                Parol
              </label>
              <Input
                id="register-password"
                type="password"
                value={form.password}
                aria-invalid={Boolean(fieldErrors.password)}
                onChange={(event) => setFieldValue("password", event.target.value)}
                placeholder="Kamida 8 ta belgi"
              />
              {fieldErrors.password && <p className="mt-1 text-xs text-red-600">{fieldErrors.password}</p>}
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="register-confirm-password">
                Parolni tasdiqlang
              </label>
              <Input
                id="register-confirm-password"
                type="password"
                value={form.confirm_password}
                aria-invalid={Boolean(fieldErrors.confirm_password)}
                onChange={(event) => setFieldValue("confirm_password", event.target.value)}
                placeholder="Qayta kiriting"
              />
              {fieldErrors.confirm_password && (
                <p className="mt-1 text-xs text-red-600">{fieldErrors.confirm_password}</p>
              )}
            </div>
          </div>

          {formError && <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{formError}</div>}

          <Button type="button" className="w-full" onClick={() => registerMutation.mutate()} disabled={registerMutation.isPending}>
            {registerMutation.isPending ? "Yuborilmoqda..." : "Ro‘yxatdan o‘tish"}
          </Button>

          <p className="text-center text-sm text-slate-600">
            Akkountingiz bormi?{" "}
            <Link href="/login" className="font-medium text-slate-900 underline">
              Login
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  )
}
