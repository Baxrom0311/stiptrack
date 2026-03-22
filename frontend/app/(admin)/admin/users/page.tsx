"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { PencilLine, Shield, UserCheck, UserCog, UserPlus, UserRoundX } from "lucide-react"
import { useMemo, useState } from "react"

import {
  adminUserCreateFormSchema,
  adminUserUpdateFormSchema,
  FieldErrors,
  getFieldErrors,
  getFirstFieldError,
} from "@/lib/form-validation"
import { extractErrorMessage, notifyError, notifySuccess } from "@/lib/notifications"
import {
  createUser,
  listUsers,
  toggleUserActive,
  updateUser,
  type UserAdminCreatePayload,
  type UserAdminUpdatePayload,
} from "@/lib/users"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import EmptyState from "@/components/ui/empty-state"
import { Input } from "@/components/ui/input"
import { FormCardSkeleton, HeroSkeleton, StatCardsSkeleton, TableCardSkeleton } from "@/components/ui/page-skeletons"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { Role, User } from "@/types"

function roleVariant(role: Role): "default" | "secondary" | "outline" | "destructive" {
  if (role === "admin") {
    return "default"
  }
  if (role === "jury") {
    return "secondary"
  }
  return "outline"
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

function formatDate(value: string): string {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }
  return new Intl.DateTimeFormat("uz-UZ", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed)
}

type AdminUserFormState = {
  full_name: string
  email: string
  password: string
  role: Role
  department: string
  student_id: string
  is_supervisor: boolean
  is_active: boolean
}

const EMPTY_FORM: AdminUserFormState = {
  full_name: "",
  email: "",
  password: "",
  role: "student",
  department: "",
  student_id: "",
  is_supervisor: false,
  is_active: true,
}

function buildCreateUserPayload(form: AdminUserFormState): UserAdminCreatePayload {
  return {
    full_name: form.full_name.trim(),
    email: form.email.trim(),
    password: form.password,
    role: form.role,
    department: form.department.trim() || null,
    student_id: form.role === "student" ? form.student_id.trim() || null : null,
    is_supervisor: form.role === "student" ? false : form.is_supervisor,
    is_active: form.is_active,
  }
}

function buildUpdateUserPayload(form: AdminUserFormState): UserAdminUpdatePayload {
  const base = {
    full_name: form.full_name.trim(),
    email: form.email.trim(),
    role: form.role,
    department: form.department.trim() || null,
    student_id: form.role === "student" ? form.student_id.trim() || null : null,
    is_supervisor: form.role === "student" ? false : form.is_supervisor,
    is_active: form.is_active,
  }

  return {
    ...base,
    ...(form.password.trim() ? { password: form.password } : {}),
  }
}

export default function AdminUsersPage() {
  const queryClient = useQueryClient()
  const [role, setRole] = useState<"all" | Role>("all")
  const [isActive, setIsActive] = useState<"all" | "active" | "inactive">("all")
  const [search, setSearch] = useState("")
  const [dialogMode, setDialogMode] = useState<"create" | "edit" | null>(null)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [form, setForm] = useState<AdminUserFormState>(EMPTY_FORM)
  const [formErrors, setFormErrors] = useState<FieldErrors<keyof AdminUserFormState>>({})
  const [formError, setFormError] = useState<string | null>(null)
  const hasActiveFilters = role !== "all" || isActive !== "all" || search.trim().length > 0

  const usersQuery = useQuery({
    queryKey: ["admin-users", role, isActive, search],
    queryFn: () =>
      listUsers({
        role: role === "all" ? undefined : role,
        is_active: isActive === "all" ? undefined : isActive === "active",
        search: search.trim() || undefined,
        limit: 200,
      }),
    retry: 0,
  })

  const toggleMutation = useMutation({
    mutationFn: (userId: string) => toggleUserActive(userId),
    onSuccess: async (user) => {
      notifySuccess(`${user.full_name} uchun active holati o‘zgartirildi.`)
      await queryClient.invalidateQueries({ queryKey: ["admin-users"] })
    },
    onError: (error) => {
      notifyError(error)
    },
  })

  const saveUserMutation = useMutation({
    mutationFn: async () => {
      const parsed =
        dialogMode === "create"
          ? adminUserCreateFormSchema.safeParse(form)
          : adminUserUpdateFormSchema.safeParse(form)

      if (!parsed.success) {
        const errors = getFieldErrors<keyof AdminUserFormState>(parsed.error)
        setFormErrors(errors)
        throw new Error(getFirstFieldError(errors) ?? "Forma noto‘g‘ri to‘ldirilgan.")
      }

      if (dialogMode === "create") {
        return createUser(buildCreateUserPayload(parsed.data))
      }

      if (!editingUser) {
        throw new Error("Tahrirlanadigan foydalanuvchi topilmadi.")
      }

      return updateUser(editingUser.id, buildUpdateUserPayload(parsed.data))
    },
    onSuccess: async (user) => {
      notifySuccess(
        dialogMode === "create"
          ? `${user.full_name} yaratildi.`
          : `${user.full_name} ma’lumotlari yangilandi.`,
      )
      setDialogMode(null)
      setEditingUser(null)
      setForm(EMPTY_FORM)
      setFormErrors({})
      setFormError(null)
      await queryClient.invalidateQueries({ queryKey: ["admin-users"] })
    },
    onError: (error) => {
      const message = extractErrorMessage(error)
      setFormError(message)
      notifyError(message)
    },
  })

  const stats = useMemo(() => {
    const items = usersQuery.data ?? []
    return {
      total: items.length,
      admins: items.filter((item) => item.role === "admin").length,
      juries: items.filter((item) => item.role === "jury").length,
      blocked: items.filter((item) => !item.is_active).length,
    }
  }, [usersQuery.data])

  function openCreateDialog() {
    setDialogMode("create")
    setEditingUser(null)
    setForm(EMPTY_FORM)
    setFormErrors({})
    setFormError(null)
  }

  function openEditDialog(user: User) {
    setDialogMode("edit")
    setEditingUser(user)
    setForm({
      full_name: user.full_name,
      email: user.email,
      password: "",
      role: user.role,
      department: user.department ?? "",
      student_id: user.student_id ?? "",
      is_supervisor: user.role === "student" ? false : user.is_supervisor,
      is_active: user.is_active,
    })
    setFormErrors({})
    setFormError(null)
  }

  function handleFormChange<K extends keyof AdminUserFormState>(field: K, value: AdminUserFormState[K]) {
    setForm((current) => {
      const next = { ...current, [field]: value }
      if (field === "role") {
        if (value === "student") {
          next.is_supervisor = false
        }
      }
      return next
    })
    setFormErrors((current) => ({ ...current, [field]: undefined }))
    setFormError(null)
  }

  if (usersQuery.isLoading) {
    return (
      <div className="grid gap-6">
        <HeroSkeleton />
        <StatCardsSkeleton />
        <FormCardSkeleton fields={3} actions={0} />
        <TableCardSkeleton rows={6} columns={6} withToolbar={false} />
      </div>
    )
  }

  return (
    <div className="grid gap-6">
      <section className="rounded-3xl bg-[linear-gradient(135deg,_#eff6ff,_#ecfccb_50%,_#f8fafc)] p-6 ring-1 ring-emerald-200">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <Badge variant="outline">User Control</Badge>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Foydalanuvchilar boshqaruvi</h1>
            <p className="max-w-3xl text-sm text-slate-700">
              Admin, jury va studentlarni bir joyda ko‘ring, qidiring, role bo‘yicha filtrlab accountni bloklang yoki
              qayta faollashtiring.
            </p>
          </div>

          <Button type="button" className="gap-2 self-start lg:self-auto" onClick={openCreateDialog}>
            <UserPlus className="h-4 w-4" />
            Yangi foydalanuvchi
          </Button>
        </div>
      </section>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Shield className="h-4 w-4 text-slate-700" />
              Total
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold text-slate-900">{stats.total}</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <UserCog className="h-4 w-4 text-sky-700" />
              Admins
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold text-slate-900">{stats.admins}</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <UserCheck className="h-4 w-4 text-emerald-700" />
              Jury
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold text-slate-900">{stats.juries}</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <UserRoundX className="h-4 w-4 text-rose-700" />
              Blocked
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold text-slate-900">{stats.blocked}</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle>Filterlar</CardTitle>
          <CardDescription>Role, active holat va qidiruv bo‘yicha foydalanuvchilarni saralang.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Ism yoki email..." />

          <select
            className="h-8 w-full rounded-lg border border-slate-300 px-2.5 text-sm"
            value={role}
            onChange={(event) => setRole(event.target.value as "all" | Role)}
          >
            <option value="all">Barcha role</option>
            <option value="admin">Admin</option>
            <option value="jury">Jury</option>
            <option value="student">Student</option>
          </select>

          <select
            className="h-8 w-full rounded-lg border border-slate-300 px-2.5 text-sm"
            value={isActive}
            onChange={(event) => setIsActive(event.target.value as "all" | "active" | "inactive")}
          >
            <option value="all">Barcha holat</option>
            <option value="active">Faqat active</option>
            <option value="inactive">Faqat blocked</option>
          </select>
        </CardContent>
      </Card>

      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle>Foydalanuvchilar jadvali</CardTitle>
          <CardDescription>Admin o‘zini bloklay olmaydi, backend shu guardni ham nazorat qiladi.</CardDescription>
        </CardHeader>
        <CardContent>
          {usersQuery.isError ? (
            <p className="text-sm text-red-600">Foydalanuvchilarni yuklab bo‘lmadi.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Department</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(usersQuery.data ?? []).map((user: User) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium text-slate-900">{user.full_name}</p>
                        <p className="text-xs text-slate-500">{user.email}</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant={roleVariant(user.role)}>{roleLabel(user.role)}</Badge>
                        {user.is_supervisor && <Badge variant="outline">Supervisor</Badge>}
                      </div>
                    </TableCell>
                    <TableCell>{user.department || "-"}</TableCell>
                    <TableCell>
                      <Badge variant={user.is_active ? "secondary" : "destructive"}>
                        {user.is_active ? "Active" : "Blocked"}
                      </Badge>
                    </TableCell>
                    <TableCell>{formatDate(user.created_at)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button type="button" variant="outline" size="sm" onClick={() => openEditDialog(user)}>
                          <PencilLine className="mr-1 h-3.5 w-3.5" />
                          Edit
                        </Button>
                        <Button
                          type="button"
                          variant={user.is_active ? "destructive" : "outline"}
                          size="sm"
                          onClick={() => toggleMutation.mutate(user.id)}
                          disabled={toggleMutation.isPending}
                        >
                          {user.is_active ? "Block" : "Unblock"}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          {!usersQuery.isLoading && !usersQuery.isError && (usersQuery.data ?? []).length === 0 && (
            <EmptyState
              className="mt-4"
              title={hasActiveFilters ? "Mos foydalanuvchi topilmadi" : "Foydalanuvchilar hali yo‘q"}
              description={
                hasActiveFilters
                  ? "Role, status yoki qidiruv shartlariga mos foydalanuvchi chiqmagan."
                  : "Tizimdagi admin, jury va studentlar shu jadvalda boshqariladi."
              }
              action={
                hasActiveFilters ? (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setRole("all")
                      setIsActive("all")
                      setSearch("")
                    }}
                  >
                    Filterlarni tozalash
                  </Button>
                ) : (
                  <Button type="button" onClick={openCreateDialog}>
                    Yangi foydalanuvchi
                  </Button>
                )
              }
            />
          )}
        </CardContent>
      </Card>

      <Dialog
        open={dialogMode !== null}
        onOpenChange={(open) => {
          if (!open) {
            setDialogMode(null)
            setEditingUser(null)
            setFormErrors({})
            setFormError(null)
          }
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>{dialogMode === "create" ? "Yangi foydalanuvchi yaratish" : "Foydalanuvchini tahrirlash"}</DialogTitle>
            <DialogDescription>
              {dialogMode === "create"
                ? "Admin, jury yoki student akkauntini qo‘lda oching."
                : "Role, status va profil ma’lumotlarini yangilang."}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4">
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="user-full-name">
                  F.I.Sh
                </label>
                <Input
                  id="user-full-name"
                  value={form.full_name}
                  aria-invalid={Boolean(formErrors.full_name)}
                  onChange={(event) => handleFormChange("full_name", event.target.value)}
                />
                {formErrors.full_name && <p className="mt-1 text-xs text-red-600">{formErrors.full_name}</p>}
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="user-email">
                  Email
                </label>
                <Input
                  id="user-email"
                  type="email"
                  value={form.email}
                  aria-invalid={Boolean(formErrors.email)}
                  onChange={(event) => handleFormChange("email", event.target.value)}
                />
                {formErrors.email && <p className="mt-1 text-xs text-red-600">{formErrors.email}</p>}
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="user-role">
                  Role
                </label>
                <select
                  id="user-role"
                  className="h-8 w-full rounded-lg border border-slate-300 px-2.5 text-sm"
                  value={form.role}
                  onChange={(event) => handleFormChange("role", event.target.value as Role)}
                >
                  <option value="admin">Admin</option>
                  <option value="jury">Jury</option>
                  <option value="student">Student</option>
                </select>
                {formErrors.role && <p className="mt-1 text-xs text-red-600">{formErrors.role}</p>}
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="user-password">
                  Parol
                </label>
                <Input
                  id="user-password"
                  type="password"
                  value={form.password}
                  aria-invalid={Boolean(formErrors.password)}
                  placeholder={dialogMode === "edit" ? "Bo‘sh qoldirsangiz o‘zgarmaydi" : "Kamida 8 belgi"}
                  onChange={(event) => handleFormChange("password", event.target.value)}
                />
                {formErrors.password && <p className="mt-1 text-xs text-red-600">{formErrors.password}</p>}
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="user-department">
                  Fakultet/Bolim
                </label>
                <Input
                  id="user-department"
                  value={form.department}
                  aria-invalid={Boolean(formErrors.department)}
                  onChange={(event) => handleFormChange("department", event.target.value)}
                />
                {formErrors.department && <p className="mt-1 text-xs text-red-600">{formErrors.department}</p>}
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="user-student-id">
                  Student ID
                </label>
                <Input
                  id="user-student-id"
                  value={form.student_id}
                  disabled={form.role !== "student"}
                  aria-invalid={Boolean(formErrors.student_id)}
                  placeholder={form.role === "student" ? "Masalan: S-2026-005" : "Faqat student uchun"}
                  onChange={(event) => handleFormChange("student_id", event.target.value)}
                />
                {formErrors.student_id && <p className="mt-1 text-xs text-red-600">{formErrors.student_id}</p>}
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <label className="flex items-center gap-2 rounded-xl border border-slate-200 p-3 text-sm">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(event) => handleFormChange("is_active", event.target.checked)}
                />
                Active akkaunt
              </label>

              <label className="flex items-center gap-2 rounded-xl border border-slate-200 p-3 text-sm">
                <input
                  type="checkbox"
                  checked={form.is_supervisor}
                  disabled={form.role === "student"}
                  onChange={(event) => handleFormChange("is_supervisor", event.target.checked)}
                />
                Ilmiy rahbar sifatida ko‘rinsin
              </label>
            </div>

            {formError && <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{formError}</div>}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setDialogMode(null)
                setEditingUser(null)
                setFormErrors({})
                setFormError(null)
              }}
            >
              Bekor qilish
            </Button>
            <Button type="button" onClick={() => saveUserMutation.mutate()} disabled={saveUserMutation.isPending}>
              {saveUserMutation.isPending
                ? "Saqlanmoqda..."
                : dialogMode === "create"
                  ? "Foydalanuvchi yaratish"
                  : "O‘zgarishlarni saqlash"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
