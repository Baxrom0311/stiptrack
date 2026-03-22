"use client"

import Link from "next/link"
import { useEffect, useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { Badge } from "@/components/ui/badge"
import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { FormCardSkeleton } from "@/components/ui/page-skeletons"
import { getMe, updateMe } from "@/lib/auth"
import { listMyApplications } from "@/lib/applications"
import { FieldErrors, getFieldErrors, getFirstFieldError, profileFormSchema } from "@/lib/form-validation"
import { extractErrorMessage, notifyError, notifySuccess } from "@/lib/notifications"
import { listSupervisors } from "@/lib/users"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/store/authStore"
import type { Role } from "@/types"

type ProfileForm = {
  full_name: string
  department: string
  student_id: string
  is_supervisor: boolean
}

const EMPTY_FORM: ProfileForm = {
  full_name: "",
  department: "",
  student_id: "",
  is_supervisor: false,
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "-"
  }
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }
  return new Intl.DateTimeFormat("uz-UZ", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed)
}

function roleLabel(role: Role): string {
  if (role === "admin") {
    return "Admin"
  }
  if (role === "jury") {
    return "Jury"
  }
  return "Student"
}

function buildRoleAction(role: Role): { href: string; label: string } {
  if (role === "admin") {
    return { href: "/admin/users", label: "Users sahifasiga o‘tish" }
  }
  if (role === "jury") {
    return { href: "/jury/applications", label: "Arizalarga o‘tish" }
  }
  return { href: "/student/applications", label: "Arizalarga o‘tish" }
}

export default function SharedProfilePage() {
  const queryClient = useQueryClient()
  const setAuthUser = useAuthStore((state) => state.setUser)
  const [form, setForm] = useState<ProfileForm>(EMPTY_FORM)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors<keyof ProfileForm>>({})
  const [formError, setFormError] = useState<string | null>(null)

  const meQuery = useQuery({
    queryKey: ["profile-me"],
    queryFn: getMe,
    retry: 0,
  })

  const role = meQuery.data?.role
  const isStudent = role === "student"

  const applicationsQuery = useQuery({
    queryKey: ["profile-my-applications"],
    queryFn: listMyApplications,
    retry: 0,
    enabled: isStudent,
  })

  const supervisorsQuery = useQuery({
    queryKey: ["profile-supervisors"],
    queryFn: listSupervisors,
    retry: 0,
    enabled: isStudent,
  })

  useEffect(() => {
    if (!meQuery.data) {
      return
    }
    setForm({
      full_name: meQuery.data.full_name ?? "",
      department: meQuery.data.department ?? "",
      student_id: meQuery.data.student_id ?? "",
      is_supervisor: meQuery.data.role === "student" ? false : meQuery.data.is_supervisor,
    })
  }, [meQuery.data])

  const supervisorInfo = useMemo(() => {
    const applications = applicationsQuery.data ?? []
    const supervisors = supervisorsQuery.data ?? []
    const supervisorMap = new Map(supervisors.map((item) => [item.id, item]))

    const latestApplication = [...applications]
      .filter((application) => Boolean(application.supervisor_id))
      .sort((a, b) => {
        const ad = new Date(a.submitted_at ?? a.created_at ?? 0).getTime()
        const bd = new Date(b.submitted_at ?? b.created_at ?? 0).getTime()
        return bd - ad
      })[0]

    if (!latestApplication?.supervisor_id) {
      return {
        supervisorName: "Tanlanmagan",
        supervisorEmail: "-",
        lastUsedAt: "-",
        totalWithSupervisor: 0,
      }
    }

    const supervisor = supervisorMap.get(latestApplication.supervisor_id)
    const totalWithSupervisor = applications.filter(
      (application) => application.supervisor_id === latestApplication.supervisor_id,
    ).length

    return {
      supervisorName: supervisor?.full_name ?? "Noma’lum ilmiy rahbar",
      supervisorEmail: supervisor?.email ?? "-",
      lastUsedAt: formatDate(latestApplication.submitted_at ?? latestApplication.created_at),
      totalWithSupervisor,
    }
  }, [applicationsQuery.data, supervisorsQuery.data])

  const updateMutation = useMutation({
    mutationFn: async () => {
      const parsed = profileFormSchema.safeParse(form)
      if (!parsed.success) {
        const errors = getFieldErrors<keyof ProfileForm>(parsed.error)
        setFieldErrors(errors)
        throw new Error(getFirstFieldError(errors) ?? "Formada xatolik bor.")
      }

      setFieldErrors({})
      setFormError(null)

      return updateMe({
        full_name: parsed.data.full_name,
        department: parsed.data.department || null,
        student_id: isStudent ? parsed.data.student_id || null : null,
        is_supervisor: isStudent ? false : parsed.data.is_supervisor,
      })
    },
    onSuccess: async (user) => {
      setAuthUser(user)
      setFormError(null)
      notifySuccess("Profil yangilandi.")
      await queryClient.invalidateQueries({ queryKey: ["profile-me"] })
    },
    onError: (error) => {
      const message = extractErrorMessage(error)
      setFormError(message)
      notifyError(message)
    },
  })

  if (meQuery.isLoading) {
    return (
      <div className="grid gap-6">
        <FormCardSkeleton fields={4} />
        <FormCardSkeleton fields={3} actions={0} />
      </div>
    )
  }

  if (meQuery.isError || !meQuery.data || !role) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Profilni yuklab bo‘lmadi</CardTitle>
          <CardDescription>Qayta kirib, yana urinib ko‘ring.</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  const me = meQuery.data
  const roleAction = buildRoleAction(role)

  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader>
          <CardTitle>{roleLabel(role)} Profili</CardTitle>
          <CardDescription>Shaxsiy akkaunt ma’lumotlari va rolga tegishli holatlar.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">Role: {roleLabel(role)}</Badge>
            <Badge variant={me.is_active ? "secondary" : "destructive"}>
              {me.is_active ? "Faol akkaunt" : "Bloklangan"}
            </Badge>
            <Badge variant="outline">Ro‘yxatdan o‘tgan: {formatDate(me.created_at)}</Badge>
            <Badge variant="outline">Oxirgi yangilanish: {formatDate(me.updated_at)}</Badge>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="profile-full-name">
                F.I.Sh
              </label>
              <Input
                id="profile-full-name"
                value={form.full_name}
                aria-invalid={Boolean(fieldErrors.full_name)}
                onChange={(event) => {
                  setForm((prev) => ({ ...prev, full_name: event.target.value }))
                  setFieldErrors((prev) => ({ ...prev, full_name: undefined }))
                  setFormError(null)
                }}
              />
              {fieldErrors.full_name && <p className="mt-1 text-xs text-red-600">{fieldErrors.full_name}</p>}
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="profile-email">
                Email
              </label>
              <Input id="profile-email" value={me.email} disabled />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="profile-department">
                Fakultet/Bolim
              </label>
              <Input
                id="profile-department"
                value={form.department}
                aria-invalid={Boolean(fieldErrors.department)}
                onChange={(event) => {
                  setForm((prev) => ({ ...prev, department: event.target.value }))
                  setFieldErrors((prev) => ({ ...prev, department: undefined }))
                  setFormError(null)
                }}
              />
              {fieldErrors.department && <p className="mt-1 text-xs text-red-600">{fieldErrors.department}</p>}
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="profile-student-id">
                Student ID
              </label>
              <Input
                id="profile-student-id"
                value={form.student_id}
                disabled={!isStudent}
                aria-invalid={Boolean(fieldErrors.student_id)}
                placeholder={isStudent ? "Masalan: S-2026-001" : "Faqat student uchun"}
                onChange={(event) => {
                  setForm((prev) => ({ ...prev, student_id: event.target.value }))
                  setFieldErrors((prev) => ({ ...prev, student_id: undefined }))
                  setFormError(null)
                }}
              />
              {fieldErrors.student_id && <p className="mt-1 text-xs text-red-600">{fieldErrors.student_id}</p>}
            </div>
          </div>

          {!isStudent && (
            <label className="flex items-center gap-2 rounded-xl border border-slate-200 p-3 text-sm">
              <input
                type="checkbox"
                checked={form.is_supervisor}
                onChange={(event) => {
                  setForm((prev) => ({ ...prev, is_supervisor: event.target.checked }))
                  setFieldErrors((prev) => ({ ...prev, is_supervisor: undefined }))
                  setFormError(null)
                }}
              />
              Ilmiy rahbar sifatida ko‘rinsin
            </label>
          )}

          {formError && <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{formError}</div>}

          <div className="flex justify-end">
            <Button type="button" onClick={() => updateMutation.mutate()} disabled={updateMutation.isPending}>
              {updateMutation.isPending ? "Saqlanmoqda..." : "Profilni saqlash"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{isStudent ? "Ilmiy Rahbar Holati" : "Akkount Xulosasi"}</CardTitle>
          <CardDescription>
            {isStudent
              ? "Arizalaringizdan aniqlangan so‘nggi ilmiy rahbar ma’lumoti."
              : "Joriy rol va akkaunt flaglari bo‘yicha umumiy ko‘rinish."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isStudent ? (
            applicationsQuery.isLoading || supervisorsQuery.isLoading ? (
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-lg border border-slate-200 p-4">
                  <div className="h-3 w-24 animate-pulse rounded-md bg-slate-200/80" />
                  <div className="mt-3 h-5 w-48 animate-pulse rounded-md bg-slate-200/80" />
                  <div className="mt-2 h-4 w-36 animate-pulse rounded-md bg-slate-200/80" />
                </div>
                <div className="rounded-lg border border-slate-200 p-4">
                  <div className="h-3 w-32 animate-pulse rounded-md bg-slate-200/80" />
                  <div className="mt-3 h-5 w-40 animate-pulse rounded-md bg-slate-200/80" />
                  <div className="mt-2 h-4 w-44 animate-pulse rounded-md bg-slate-200/80" />
                </div>
              </div>
            ) : (
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-lg border border-slate-200 p-4">
                  <p className="text-xs text-slate-500">Ilmiy rahbar</p>
                  <p className="mt-1 text-sm font-semibold text-slate-900">{supervisorInfo.supervisorName}</p>
                  <p className="mt-1 text-xs text-slate-600">{supervisorInfo.supervisorEmail}</p>
                </div>
                <div className="rounded-lg border border-slate-200 p-4">
                  <p className="text-xs text-slate-500">So‘nggi qo‘llangan vaqt</p>
                  <p className="mt-1 text-sm font-semibold text-slate-900">{supervisorInfo.lastUsedAt}</p>
                  <p className="mt-1 text-xs text-slate-600">
                    Shu rahbar bilan arizalar soni: {supervisorInfo.totalWithSupervisor}
                  </p>
                </div>
              </div>
            )
          ) : (
            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-lg border border-slate-200 p-4">
                <p className="text-xs text-slate-500">Role</p>
                <p className="mt-1 text-sm font-semibold text-slate-900">{roleLabel(role)}</p>
              </div>
              <div className="rounded-lg border border-slate-200 p-4">
                <p className="text-xs text-slate-500">Supervisor flag</p>
                <p className="mt-1 text-sm font-semibold text-slate-900">
                  {me.is_supervisor ? "Yoqilgan" : "O‘chirilgan"}
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 p-4">
                <p className="text-xs text-slate-500">Status</p>
                <p className="mt-1 text-sm font-semibold text-slate-900">{me.is_active ? "Active" : "Blocked"}</p>
              </div>
            </div>
          )}

          <div className="flex justify-end">
            <Link href={roleAction.href} className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
              {roleAction.label}
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
