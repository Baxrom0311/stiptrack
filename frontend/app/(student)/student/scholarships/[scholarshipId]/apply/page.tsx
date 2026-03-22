"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect, useMemo, useState } from "react"

import DynamicForm, {
  buildDynamicInitialValues,
  type DynamicFormValues,
  validateDynamicValues,
} from "@/components/application/DynamicForm"
import { Badge } from "@/components/ui/badge"
import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import EmptyState from "@/components/ui/empty-state"
import { DetailPageSkeleton } from "@/components/ui/page-skeletons"
import {
  getScholarshipApplicationDraft,
  submitApplication,
  updateApplicationDraft,
  uploadApplicationValueFile,
} from "@/lib/applications"
import { notifyError, notifySuccess, notifyWarning } from "@/lib/notifications"
import { getScholarship } from "@/lib/scholarships"
import { cn } from "@/lib/utils"
import { listSupervisors } from "@/lib/users"
import type { ApplicationDetailResponse, ApplicationValueDetail, Column } from "@/types"

type StudentScholarshipApplyPageProps = {
  params: {
    scholarshipId: string
  }
}

function upsertApplicationValue(
  values: ApplicationValueDetail[],
  column: Column,
  patch: Partial<ApplicationValueDetail>,
): ApplicationValueDetail[] {
  const existing = values.find((item) => item.column_id === column.id)
  if (!existing) {
    return [
      ...values,
      {
        id: `temp-${column.id}`,
        column_id: column.id,
        value_text: null,
        value_file_url: null,
        ai_analysis: null,
        ai_score: null,
        column,
        ...patch,
      },
    ]
  }

  return values.map((item) => {
    if (item.column_id !== column.id) {
      return item
    }
    return {
      ...item,
      ...patch,
    }
  })
}

function formatDeadline(value: string | null | undefined): string {
  if (!value) {
    return "Ko‘rsatilmagan"
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

export default function StudentScholarshipApplyPage({ params }: StudentScholarshipApplyPageProps) {
  const router = useRouter()
  const queryClient = useQueryClient()
  const scholarshipId = params.scholarshipId?.trim()
  const [formValues, setFormValues] = useState<DynamicFormValues>({})
  const [supervisorId, setSupervisorId] = useState("")
  const [submitAttempted, setSubmitAttempted] = useState(false)

  const scholarshipQuery = useQuery({
    queryKey: ["student-scholarship-detail", scholarshipId],
    queryFn: () => getScholarship(scholarshipId as string),
    enabled: Boolean(scholarshipId),
    retry: 0,
  })

  const draftQuery = useQuery({
    queryKey: ["student-scholarship-draft", scholarshipId],
    queryFn: () => getScholarshipApplicationDraft(scholarshipId as string),
    enabled: Boolean(scholarshipId) && scholarshipQuery.data?.status === "open",
    retry: 0,
  })

  const supervisorsQuery = useQuery({
    queryKey: ["student-supervisors"],
    queryFn: listSupervisors,
    enabled: scholarshipQuery.data?.status === "open",
    retry: 0,
  })

  useEffect(() => {
    setSupervisorId(draftQuery.data?.supervisor?.id ?? "")
  }, [draftQuery.data?.supervisor?.id])

  const formColumns = useMemo(() => scholarshipQuery.data?.columns ?? [], [scholarshipQuery.data?.columns])
  const initialValues = useMemo(
    () => buildDynamicInitialValues(formColumns, draftQuery.data?.values ?? []),
    [draftQuery.data?.values, formColumns],
  )

  const saveDraftMutation = useMutation({
    mutationFn: async (payload: { supervisor_id?: string | null; values?: Record<string, string | null> }) => {
      if (!draftQuery.data?.id) {
        throw new Error("Ariza hali tayyor emas")
      }
      return updateApplicationDraft(draftQuery.data.id, payload)
    },
  })

  const submitMutation = useMutation({
    mutationFn: async () => {
      if (!draftQuery.data?.id) {
        throw new Error("Ariza topilmadi")
      }
      return submitApplication(draftQuery.data.id)
    },
    onSuccess: async (submitted) => {
      notifySuccess("Ariza muvaffaqiyatli topshirildi.")
      await queryClient.invalidateQueries({ queryKey: ["student-my-applications"] })
      await queryClient.invalidateQueries({ queryKey: ["my-applications"] })
      await queryClient.invalidateQueries({ queryKey: ["student-dashboard-applications"] })
      router.push(`/student/applications/${submitted.id}/result`)
    },
    onError: (error) => {
      notifyError(error)
    },
  })

  if (!scholarshipId) {
    return null
  }

  if (scholarshipQuery.isLoading || (scholarshipQuery.data?.status === "open" && draftQuery.isLoading)) {
    return <DetailPageSkeleton className="xl:grid-cols-[1.3fr_0.9fr]" />
  }

  if (scholarshipQuery.isError || !scholarshipQuery.data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Stipendiya topilmadi</CardTitle>
          <CardDescription>Ushbu stipendiya mavjud emas yoki o‘chirilgan.</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  const scholarship = scholarshipQuery.data

  if (scholarship.status !== "open") {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Ariza topshirish yopiq</CardTitle>
          <CardDescription>Faqat `open` holatdagi stipendiyaga ariza topshirish mumkin.</CardDescription>
        </CardHeader>
        <CardContent>
          <Link href="/student/scholarships" className={cn(buttonVariants({ variant: "outline" }))}>
            Ochiq stipendiyalarga qaytish
          </Link>
        </CardContent>
      </Card>
    )
  }

  if (draftQuery.isError || !draftQuery.data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Ariza formasini yuklab bo‘lmadi</CardTitle>
          <CardDescription>Serverdan draft ariza holatini olishda xatolik bo‘ldi.</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  const application = draftQuery.data
  const validationErrors = validateDynamicValues(formColumns, formValues)

  async function handleSupervisorChange(nextSupervisorId: string) {
    setSupervisorId(nextSupervisorId)

    try {
      await saveDraftMutation.mutateAsync({
        supervisor_id: nextSupervisorId || null,
      })
    } catch (error) {
      notifyError(error, "Ilmiy rahbarni saqlab bo‘lmadi.")
    }
  }

  async function handleSubmit() {
    setSubmitAttempted(true)
    const firstError = Object.values(validationErrors)[0]
    if (firstError) {
      notifyWarning(firstError)
      return
    }
    await submitMutation.mutateAsync()
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[1.35fr_0.95fr]">
      <div className="space-y-6">
        <section className="rounded-3xl bg-[linear-gradient(135deg,_#eff6ff,_#f0fdf4_55%,_#f8fafc)] p-6 ring-1 ring-sky-200">
          <div className="space-y-2">
            <Badge variant="outline">Student Apply</Badge>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-900">{scholarship.title}</h1>
            <p className="max-w-3xl text-sm text-slate-600">{scholarship.description || "Stipendiya uchun dinamik ariza formasi."}</p>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Badge variant="secondary">Deadline: {formatDeadline(scholarship.deadline)}</Badge>
            <Badge variant="outline">Ustunlar: {formColumns.length}</Badge>
            <Badge variant="outline">Draft ID: {application.id}</Badge>
          </div>
        </section>

        {formColumns.length === 0 ? (
          <Card>
            <CardContent className="pt-6">
              <EmptyState
                title="Forma maydonlari hali yo‘q"
                description="Admin bu stipendiya uchun ustunlarni hali yaratmagan. Ustunlar qo‘shilgach shu yerda dinamik forma paydo bo‘ladi."
              />
            </CardContent>
          </Card>
        ) : (
          <DynamicForm
            columns={formColumns}
            initialValues={initialValues}
            submitAttempted={submitAttempted}
            disabled={submitMutation.isPending}
            onValuesChange={setFormValues}
            onAutosave={async (values) => {
              await saveDraftMutation.mutateAsync({ values })
            }}
            onFileUpload={async (column, file, onProgress) => {
              const fileUrl = await uploadApplicationValueFile(application.id, column.id, file, onProgress)
              queryClient.setQueryData(["student-scholarship-draft", scholarshipId], (current: ApplicationDetailResponse | undefined) => {
                if (!current) {
                  return current
                }
                return {
                  ...current,
                  values: upsertApplicationValue(current.values, column, {
                    value_text: null,
                    value_file_url: fileUrl,
                  }),
                }
              })
              notifySuccess(`${column.name} uchun fayl yuklandi.`)
              return fileUrl
            }}
            onFileDelete={async (column) => {
              await saveDraftMutation.mutateAsync({ values: { [column.id]: null } })
              queryClient.setQueryData(["student-scholarship-draft", scholarshipId], (current: ApplicationDetailResponse | undefined) => {
                if (!current) {
                  return current
                }
                return {
                  ...current,
                  values: upsertApplicationValue(current.values, column, {
                    value_file_url: null,
                  }),
                }
              })
              notifySuccess(`${column.name} fayli o‘chirildi.`)
            }}
          />
        )}
      </div>

      <div className="space-y-6">
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle>Qo‘shimcha ma’lumot</CardTitle>
            <CardDescription>Ariza topshirishdan oldin ilmiy rahbarni belgilang va tekshiruvni yakunlang.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-900" htmlFor="supervisor_id">
                Ilmiy rahbar
              </label>
              <select
                id="supervisor_id"
                className="flex h-10 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                value={supervisorId}
                disabled={supervisorsQuery.isLoading || saveDraftMutation.isPending || submitMutation.isPending}
                onChange={(event) => {
                  void handleSupervisorChange(event.target.value)
                }}
              >
                <option value="">Tanlanmagan</option>
                {(supervisorsQuery.data ?? []).map((supervisor) => (
                  <option key={supervisor.id} value={supervisor.id}>
                    {supervisor.full_name} {supervisor.department ? `(${supervisor.department})` : ""}
                  </option>
                ))}
              </select>
              {supervisorsQuery.isError && <p className="text-sm text-rose-600">Rahbarlar ro‘yxatini yuklab bo‘lmadi.</p>}
            </div>

            <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
              <p className="font-medium text-slate-900">Eslatma</p>
              <ul className="mt-2 space-y-1">
                <li>Maydonlar 2 soniyadan keyin avtomatik draft sifatida saqlanadi.</li>
                <li>Majburiy maydonlar `*` bilan belgilangan.</li>
                <li>File fieldlar yuklangach darhol serverga saqlanadi.</li>
              </ul>
            </div>

            <div className="flex flex-col gap-3">
              <Button type="button" className="w-full" onClick={() => void handleSubmit()} disabled={submitMutation.isPending || formColumns.length === 0}>
                {submitMutation.isPending ? "Yuborilmoqda..." : "Arizani topshirish"}
              </Button>
              <Link href="/student/scholarships" className={cn(buttonVariants({ variant: "outline" }), "w-full") }>
                Ochiq stipendiyalarga qaytish
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
