"use client"

import Link from "next/link"
import { useQuery } from "@tanstack/react-query"

import ApplicationStatusHistory from "@/components/application/ApplicationStatusHistory"
import PlagiarismSummary from "@/components/application/PlagiarismSummary"
import { useApplication } from "@/hooks/useApplications"
import { getApplicationConsistency } from "@/lib/admin"
import { listApplicationStatusLogs } from "@/lib/applications"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import EmptyState from "@/components/ui/empty-state"
import { DetailPageSkeleton } from "@/components/ui/page-skeletons"
import type { ApplicationStatus } from "@/types"

type AdminApplicationDetailPageProps = {
  params: {
    applicationId: string
  }
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

function applicationStatusLabel(status: ApplicationStatus): string {
  if (status === "draft") {
    return "Qoralama"
  }
  if (status === "submitted") {
    return "Topshirilgan"
  }
  if (status === "in_review") {
    return "Ko‘rib chiqilmoqda"
  }
  if (status === "winner") {
    return "G‘olib"
  }
  return "Rad etilgan"
}

function statusBadgeVariant(status: ApplicationStatus): "default" | "secondary" | "outline" | "destructive" {
  if (status === "winner") {
    return "default"
  }
  if (status === "rejected") {
    return "destructive"
  }
  if (status === "submitted") {
    return "secondary"
  }
  return "outline"
}

export default function AdminApplicationDetailPage({ params }: AdminApplicationDetailPageProps) {
  const applicationId = params.applicationId?.trim()
  const query = useApplication(applicationId)
  const historyQuery = useQuery({
    queryKey: ["admin-application-history", applicationId],
    queryFn: () => listApplicationStatusLogs(applicationId as string),
    enabled: Boolean(applicationId),
    retry: 0,
  })
  const consistencyQuery = useQuery({
    queryKey: ["admin-application-consistency", applicationId],
    queryFn: () => getApplicationConsistency(applicationId as string),
    enabled: Boolean(applicationId),
    retry: 0,
  })

  if (!applicationId) {
    return null
  }

  if (query.isLoading || historyQuery.isLoading || consistencyQuery.isLoading) {
    return <DetailPageSkeleton className="xl:grid-cols-[1.2fr_0.9fr]" />
  }

  if (query.isError || !query.data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Ariza topilmadi</CardTitle>
          <CardDescription>Bu ariza mavjud emas yoki admin uchun ochiq emas.</CardDescription>
        </CardHeader>
        <CardContent>
          <Link className={buttonVariants({ variant: "outline" })} href="/admin/applications">
            Orqaga qaytish
          </Link>
        </CardContent>
      </Card>
    )
  }

  const application = query.data

  return (
    <div className="grid gap-6 xl:grid-cols-[1.2fr_0.9fr]">
      <div className="space-y-6">
        <section className="rounded-3xl bg-[linear-gradient(135deg,_#eff6ff,_#f8fafc_55%,_#fff7ed)] p-6 ring-1 ring-sky-200">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={statusBadgeVariant(application.status)}>{applicationStatusLabel(application.status)}</Badge>
                {typeof application.total_score === "number" && <Badge variant="outline">Ball: {application.total_score.toFixed(2)}</Badge>}
              </div>
              <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Ariza detail</h1>
              <p className="max-w-3xl text-sm text-slate-600">ID: {application.id}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link href="/admin/applications" className={cn(buttonVariants({ variant: "outline" }))}>
                Arizalar ro‘yxati
              </Link>
            </div>
          </div>
        </section>

        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle>Ariza qiymatlari</CardTitle>
            <CardDescription>Barcha maydonlar, yuklangan fayllar va AI tahlillar shu yerda.</CardDescription>
          </CardHeader>
          <CardContent>
            {application.values.length === 0 ? (
              <EmptyState
                title="Qiymatlar topilmadi"
                description="Bu ariza uchun hozircha hech qanday value saqlanmagan. Draft yoki buzilgan data bo‘lishi mumkin."
              />
            ) : (
              <div className="grid gap-4">
                {application.values.map((value) => (
                  <div key={value.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-slate-900">{value.column?.name ?? value.column_id}</p>
                      {value.column?.field_type && <Badge variant="outline">{value.column.field_type}</Badge>}
                      {value.column?.is_required && <Badge variant="secondary">Majburiy</Badge>}
                      {typeof value.ai_score === "number" && <Badge variant="outline">AI score: {value.ai_score}</Badge>}
                    </div>

                    {value.column?.description && <p className="mt-2 text-sm text-slate-600">{value.column.description}</p>}

                    {value.value_text && (
                      <div className="mt-3 rounded-xl bg-slate-50 p-3 text-sm text-slate-700">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Matn qiymati</p>
                        <p className="mt-1 whitespace-pre-wrap">{value.value_text}</p>
                      </div>
                    )}

                    {value.value_file_url && (
                      <div className="mt-3 rounded-xl bg-slate-50 p-3 text-sm text-slate-700">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Yuklangan fayl</p>
                        <Link href={value.value_file_url} target="_blank" className="mt-1 inline-block text-sky-700 underline">
                          Faylni ochish
                        </Link>
                      </div>
                    )}

                    <div className="mt-3 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-3 text-sm text-slate-700">
                      <p className="text-xs uppercase tracking-wide text-slate-500">AI analysis</p>
                      <p className="mt-1 whitespace-pre-wrap">{value.ai_analysis || "Bu field uchun AI tahlil saqlanmagan."}</p>
                    </div>

                    {(value.value_text || value.plagiarism_checked_at || (value.plagiarism_matches?.length ?? 0) > 0) && (
                      <PlagiarismSummary value={value} canOpenMatches />
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="space-y-6">
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle>Asosiy ma’lumotlar</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-700">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Stipendiya</p>
              <p className="mt-1 font-medium text-slate-900">{application.scholarship?.title || "Noma’lum"}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Talaba</p>
              <p className="mt-1 font-medium text-slate-900">{application.student?.full_name || "Noma’lum"}</p>
              <p className="text-slate-500">{application.student?.email || "-"}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Ilmiy rahbar</p>
              <p className="mt-1 font-medium text-slate-900">{application.supervisor?.full_name || "Tanlanmagan"}</p>
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-1">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Topshirilgan sana</p>
                <p className="mt-1">{formatDate(application.submitted_at)}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Yaratilgan</p>
                <p className="mt-1">{formatDate(application.created_at)}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Yangilangan</p>
                <p className="mt-1">{formatDate(application.updated_at)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle>Hakamlar konsistensiyasi</CardTitle>
            <CardDescription>Submitted baholar o‘rtasidagi farq va hakamlar kesimidagi tafovut.</CardDescription>
          </CardHeader>
          <CardContent>
            {!consistencyQuery.data || consistencyQuery.data.summary.jury_count === 0 ? (
              <EmptyState
                title="Consistency data topilmadi"
                description="Kamida bitta submitted baholash bo‘lgandan keyin hakamlar orasidagi farq shu yerda ko‘rinadi."
              />
            ) : (
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  <Badge variant={consistencyQuery.data.summary.is_flagged ? "destructive" : "secondary"}>
                    {consistencyQuery.data.summary.is_flagged ? "Needs review" : "Consistent"}
                  </Badge>
                  <Badge variant="outline">{consistencyQuery.data.summary.jury_count} hakam</Badge>
                  <Badge variant="outline">
                    Avg: {typeof consistencyQuery.data.summary.average_score === "number" ? consistencyQuery.data.summary.average_score.toFixed(2) : "-"}
                  </Badge>
                  <Badge variant="outline">
                    Spread: {typeof consistencyQuery.data.summary.score_spread === "number" ? consistencyQuery.data.summary.score_spread.toFixed(2) : "-"}
                  </Badge>
                  <Badge variant="outline">
                    StdDev: {typeof consistencyQuery.data.summary.score_stddev === "number" ? consistencyQuery.data.summary.score_stddev.toFixed(2) : "-"}
                  </Badge>
                </div>

                <div className="grid gap-3">
                  {consistencyQuery.data.evaluations.map((item) => (
                    <div key={item.evaluation_id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <p className="font-semibold text-slate-900">{item.jury_name}</p>
                          <p className="text-xs text-slate-500">{item.jury_id}</p>
                        </div>
                        <Badge variant="outline">
                          {typeof item.total_score === "number" ? item.total_score.toFixed(2) : "-"}
                        </Badge>
                      </div>
                      <p className="mt-2 text-xs uppercase tracking-wide text-slate-500">Submitted</p>
                      <p className="mt-1 text-sm text-slate-700">{formatDate(item.submitted_at)}</p>
                      <p className="mt-3 text-xs uppercase tracking-wide text-slate-500">Final comment</p>
                      <p className="mt-1 text-sm whitespace-pre-wrap text-slate-700">
                        {item.final_comment || "Izoh kiritilmagan."}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle>Umumiy AI xulosa</CardTitle>
            <CardDescription>Application darajasida saqlangan AI summary.</CardDescription>
          </CardHeader>
          <CardContent>
            {application.ai_summary ? (
              <div className="rounded-2xl bg-slate-50 p-4 text-sm whitespace-pre-wrap text-slate-700">{application.ai_summary}</div>
            ) : (
              <EmptyState
                title="AI summary topilmadi"
                description="Bu ariza uchun umumiy AI summary hali generatsiya qilinmagan yoki saqlanmagan."
              />
            )}
          </CardContent>
        </Card>

        <ApplicationStatusHistory
          logs={historyQuery.data ?? []}
          description="Admin ko‘rinishida ariza holati qachon va kim tomonidan o‘zgargani ko‘rinadi."
        />
      </div>
    </div>
  )
}
