"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import Link from "next/link"
import { useMemo, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { ListCardsSkeleton } from "@/components/ui/page-skeletons"
import { Textarea } from "@/components/ui/textarea"
import EmptyState from "@/components/ui/empty-state"
import {
  AchievementKind,
  createAchievement,
  deleteAchievement,
  listAchievements,
  updateAchievement,
  uploadAchievementFile,
} from "@/lib/achievements"
import { formatFileSizeLimit, getFileValidationRule, validateSelectedFile } from "@/lib/file-validation"
import { FieldErrors, achievementFormSchema, getFieldErrors, getFirstFieldError } from "@/lib/form-validation"
import { extractErrorMessage, notifyError, notifySuccess } from "@/lib/notifications"
import { cn } from "@/lib/utils"
import type { Achievement } from "@/types"

type FormState = {
  title: string
  type: AchievementKind | "none"
  date: string
  description: string
}

const TYPE_OPTIONS: Array<{ value: AchievementKind; label: string }> = [
  { value: "paper", label: "Maqola" },
  { value: "award", label: "Mukofot" },
  { value: "project", label: "Loyiha" },
  { value: "cert", label: "Sertifikat" },
  { value: "olympiad", label: "Olimpiada" },
  { value: "other", label: "Boshqa" },
]

const EMPTY_FORM: FormState = {
  title: "",
  type: "none",
  date: "",
  description: "",
}

const ACHIEVEMENT_FILE_RULE = getFileValidationRule("achievement")

function typeLabel(type: Achievement["type"]): string {
  const option = TYPE_OPTIONS.find((item) => item.value === type)
  return option?.label ?? "Tur belgilanmagan"
}

function fileExtension(url: string): string {
  const normalized = url.split("?")[0]?.split("#")[0] ?? ""
  const parts = normalized.split(".")
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : ""
}

function isPdf(url: string): boolean {
  return fileExtension(url) === "pdf"
}

function isImage(url: string): boolean {
  const ext = fileExtension(url)
  return ["png", "jpg", "jpeg", "gif", "webp", "svg"].includes(ext)
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "-"
  }
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }
  return new Intl.DateTimeFormat("uz-UZ", { dateStyle: "medium" }).format(parsed)
}

export default function StudentAchievementsPage() {
  const queryClient = useQueryClient()

  const [typeFilter, setTypeFilter] = useState<AchievementKind | "all">("all")
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Achievement | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [formFile, setFormFile] = useState<File | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors<keyof FormState>>({})

  const achievementsQuery = useQuery({
    queryKey: ["student-achievements", typeFilter],
    queryFn: () => listAchievements(typeFilter),
    retry: 0,
  })

  const saveMutation = useMutation({
    mutationFn: async () => {
      const parsed = achievementFormSchema.safeParse(form)
      if (!parsed.success) {
        const errors = getFieldErrors<keyof FormState>(parsed.error)
        setFieldErrors(errors)
        throw new Error(getFirstFieldError(errors) ?? "Formada xatolik bor.")
      }

      setFieldErrors({})
      setFormError(null)

      const payload = {
        title: parsed.data.title,
        type: parsed.data.type === "none" ? null : parsed.data.type,
        date: parsed.data.date || null,
        description: parsed.data.description || null,
      }

      let achievement: Achievement
      if (editing) {
        achievement = await updateAchievement(editing.id, payload)
      } else {
        achievement = await createAchievement(payload)
      }

      if (formFile) {
        const validationError = validateSelectedFile(formFile, "achievement")
        if (validationError) {
          throw new Error(validationError)
        }
        await uploadAchievementFile(achievement.id, formFile)
      }
      return achievement
    },
    onSuccess: async () => {
      setDialogOpen(false)
      setEditing(null)
      setForm(EMPTY_FORM)
      setFormFile(null)
      setFormError(null)
      setFieldErrors({})
      notifySuccess("Yutuq saqlandi.")
      await queryClient.invalidateQueries({ queryKey: ["student-achievements"] })
    },
    onError: (error) => {
      const errorMessage = error instanceof Error ? error.message : extractErrorMessage(error)
      setFormError(errorMessage)
      notifyError(errorMessage)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (achievementId: string) => {
      await deleteAchievement(achievementId)
    },
    onSuccess: async () => {
      notifySuccess("Yutuq o‘chirildi.")
      await queryClient.invalidateQueries({ queryKey: ["student-achievements"] })
    },
    onError: (error) => {
      notifyError(error)
    },
  })

  const openCreateDialog = () => {
    setEditing(null)
    setForm(EMPTY_FORM)
    setFormFile(null)
    setFormError(null)
    setFieldErrors({})
    setDialogOpen(true)
  }

  const openEditDialog = (achievement: Achievement) => {
    setEditing(achievement)
    setForm({
      title: achievement.title ?? "",
      type: achievement.type ?? "none",
      date: achievement.date ?? "",
      description: achievement.description ?? "",
    })
    setFormFile(null)
    setFormError(null)
    setFieldErrors({})
    setDialogOpen(true)
  }

  const achievements = useMemo(() => achievementsQuery.data ?? [], [achievementsQuery.data])

  if (achievementsQuery.isLoading) {
    return <ListCardsSkeleton count={4} />
  }

  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Yutuqlar Portfeli</CardTitle>
          <CardDescription>Yutuqlarni tur bo‘yicha boshqaring, fayl biriktiring va ko‘rib chiqing.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-slate-700" htmlFor="achievement-filter">
                Filter:
              </label>
              <select
                id="achievement-filter"
                className="h-8 rounded-lg border border-slate-300 px-2.5 text-sm"
                value={typeFilter}
                onChange={(event) => setTypeFilter(event.target.value as AchievementKind | "all")}
              >
                <option value="all">Barchasi</option>
                {TYPE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <Button type="button" onClick={openCreateDialog}>
              Yangi yutuq qo‘shish
            </Button>
          </div>
          {achievementsQuery.isError && (
            <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
              Yutuqlarni yuklab bo‘lmadi. Qayta urinib ko‘ring.
            </div>
          )}

          {!achievementsQuery.isLoading && !achievementsQuery.isError && achievements.length === 0 && (
            <EmptyState
              title="Portfel hali bo‘sh"
              description="Maqola, sertifikat, olimpiada yoki boshqa yutuqlaringizni qo‘shing. Keyingi stipendiya topshirish jarayonida shu portfel foydali bo‘ladi."
              action={
                <Button type="button" onClick={openCreateDialog}>
                  Yutuq qo‘shish
                </Button>
              }
            />
          )}

          <div className="grid gap-4">
            {achievements.map((achievement) => (
              <Card key={achievement.id} className="border-slate-200">
                <CardHeader>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <CardTitle className="text-base">{achievement.title}</CardTitle>
                      <CardDescription>Sana: {formatDate(achievement.date ?? achievement.created_at)}</CardDescription>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline">{typeLabel(achievement.type)}</Badge>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => openEditDialog(achievement)}
                      >
                        Tahrirlash
                      </Button>
                      <Button
                        type="button"
                        variant="destructive"
                        size="sm"
                        disabled={deleteMutation.isPending}
                        onClick={() => {
                          const confirmed = window.confirm("Yutuqni o‘chirmoqchimisiz?")
                          if (confirmed) {
                            deleteMutation.mutate(achievement.id)
                          }
                        }}
                      >
                        O‘chirish
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  {achievement.description && <p className="text-sm text-slate-700">{achievement.description}</p>}
                  {achievement.file_url ? (
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="secondary">Fayl biriktirilgan</Badge>
                        <Link
                          href={achievement.file_url}
                          target="_blank"
                          className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                        >
                          Faylni ochish
                        </Link>
                      </div>

                      {isPdf(achievement.file_url) && (
                        <iframe
                          title={`pdf-${achievement.id}`}
                          src={achievement.file_url}
                          className="h-72 w-full rounded-md border border-slate-200"
                        />
                      )}

                      {isImage(achievement.file_url) && (
                        <div
                          className="h-56 w-full rounded-md border border-slate-200 bg-cover bg-center bg-no-repeat"
                          style={{ backgroundImage: `url(${achievement.file_url})` }}
                        />
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500">Fayl biriktirilmagan.</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      <Dialog
        open={dialogOpen}
        onOpenChange={(open) => {
          setDialogOpen(open)
          if (!open) {
            setFieldErrors({})
            setFormError(null)
          }
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>{editing ? "Yutuqni tahrirlash" : "Yangi yutuq qo‘shish"}</DialogTitle>
            <DialogDescription>
              Asosiy ma’lumotlarni kiriting va ixtiyoriy ravishda fayl biriktiring.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="ach-title">
                Sarlavha *
              </label>
              <Input
                id="ach-title"
                value={form.title}
                aria-invalid={Boolean(fieldErrors.title)}
                onChange={(event) => {
                  setForm((prev) => ({ ...prev, title: event.target.value }))
                  setFieldErrors((prev) => ({ ...prev, title: undefined }))
                  setFormError(null)
                }}
                placeholder="Masalan: Respublika olimpiadasi g‘olibi"
              />
              {fieldErrors.title && <p className="mt-1 text-xs text-red-600">{fieldErrors.title}</p>}
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="ach-type">
                  Turi
                </label>
                <select
                  id="ach-type"
                  className="h-8 w-full rounded-lg border border-slate-300 px-2.5 text-sm"
                  value={form.type}
                  onChange={(event) => {
                    setForm((prev) => ({ ...prev, type: event.target.value as FormState["type"] }))
                    setFieldErrors((prev) => ({ ...prev, type: undefined }))
                    setFormError(null)
                  }}
                >
                  <option value="none">Tanlanmagan</option>
                  {TYPE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="ach-date">
                  Sana
                </label>
                <Input
                  id="ach-date"
                  type="date"
                  value={form.date}
                  aria-invalid={Boolean(fieldErrors.date)}
                  onChange={(event) => {
                    setForm((prev) => ({ ...prev, date: event.target.value }))
                    setFieldErrors((prev) => ({ ...prev, date: undefined }))
                    setFormError(null)
                  }}
                />
                {fieldErrors.date && <p className="mt-1 text-xs text-red-600">{fieldErrors.date}</p>}
              </div>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="ach-description">
                Tavsif
              </label>
              <Textarea
                id="ach-description"
                value={form.description}
                aria-invalid={Boolean(fieldErrors.description)}
                onChange={(event) => {
                  setForm((prev) => ({ ...prev, description: event.target.value }))
                  setFieldErrors((prev) => ({ ...prev, description: undefined }))
                  setFormError(null)
                }}
                placeholder="Yutuq tafsilotlari..."
              />
              {fieldErrors.description && <p className="mt-1 text-xs text-red-600">{fieldErrors.description}</p>}
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="ach-file">
                Fayl (PDF yoki rasm)
              </label>
              <Input
                id="ach-file"
                type="file"
                accept={ACHIEVEMENT_FILE_RULE.accept}
                onChange={(event) => {
                  const nextFile = event.target.files?.[0] ?? null
                  if (!nextFile) {
                    setFormFile(null)
                    return
                  }
                  const validationError = validateSelectedFile(nextFile, "achievement")
                  if (validationError) {
                    setFormFile(null)
                    setFormError(validationError)
                    notifyError(validationError)
                    return
                  }
                  setFormError(null)
                  setFormFile(nextFile)
                }}
              />
              {formFile && <p className="mt-1 text-xs text-slate-500">Tanlangan fayl: {formFile.name}</p>}
              <p className="mt-1 text-xs text-slate-500">
                Faqat PDF, JPG, PNG, WEBP. Maksimal hajm: {formatFileSizeLimit(ACHIEVEMENT_FILE_RULE.maxSizeBytes)}.
              </p>
            </div>

            {formError && <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{formError}</div>}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setDialogOpen(false)}
              disabled={saveMutation.isPending}
            >
              Bekor qilish
            </Button>
            <Button type="button" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? "Saqlanmoqda..." : "Saqlash"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
