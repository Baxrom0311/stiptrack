"use client"

import { useQuery } from "@tanstack/react-query"
import Link from "next/link"

import PlagiarismSummary from "@/components/application/PlagiarismSummary"
import ScoringPanel from "@/components/evaluation/ScoringPanel"
import { Badge } from "@/components/ui/badge"
import { buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { DetailPageSkeleton } from "@/components/ui/page-skeletons"
import { getApplication } from "@/lib/applications"

type JuryApplicationDetailPageProps = {
  params: {
    applicationId: string
  }
}

export default function JuryApplicationDetailPage({ params }: JuryApplicationDetailPageProps) {
  const applicationId = params.applicationId?.trim()

  const query = useQuery({
    queryKey: ["jury-application-detail", applicationId],
    queryFn: () => getApplication(applicationId as string),
    enabled: Boolean(applicationId),
    retry: 0,
  })

  if (!applicationId) {
    return null
  }

  if (query.isLoading) {
    return <DetailPageSkeleton />
  }

  if (query.isError || !query.data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Ariza topilmadi</CardTitle>
          <CardDescription>Bu arizaga kirish huquqingiz yo‘q yoki ID noto‘g‘ri.</CardDescription>
        </CardHeader>
        <CardContent>
          <Link className={buttonVariants({ variant: "outline" })} href="/jury/applications">
            Orqaga qaytish
          </Link>
        </CardContent>
      </Card>
    )
  }

  const application = query.data
  const isBlindReview = Boolean(application.scholarship?.blind_review_enabled)
  const participantLabel = isBlindReview
    ? `Anonim ishtirokchi #${application.id.slice(0, 8)}`
    : application.student?.full_name ?? "Noma'lum"

  return (
    <div className="grid gap-6 xl:grid-cols-[1.2fr_1fr]">
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Ariza Detail</CardTitle>
            <CardDescription>ID: {application.id}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Badge variant="outline">Status: {application.status}</Badge>
            {application.total_score !== null && application.total_score !== undefined && (
              <Badge variant="secondary">Total: {application.total_score}</Badge>
            )}
            {application.scholarship?.title && <Badge>Stipendiya: {application.scholarship.title}</Badge>}
            <Badge variant="outline">Ishtirokchi: {participantLabel}</Badge>
            {isBlindReview && <Badge variant="secondary">Blind review</Badge>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ishtirokchi ma’lumotlari</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-slate-700">
            {isBlindReview ? (
              <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 p-3">
                <p className="font-medium text-slate-900">Blind review faol</p>
                <p className="mt-1 text-slate-600">
                  Talaba va ilmiy rahbar identifikatsiya ma’lumotlari jury uchun yashirilgan.
                </p>
              </div>
            ) : (
              <>
                <p>
                  <span className="font-medium">F.I.Sh:</span> {application.student?.full_name || "Noma'lum"}
                </p>
                <p>
                  <span className="font-medium">Email:</span> {application.student?.email || "Noma'lum"}
                </p>
                <p>
                  <span className="font-medium">Ilmiy rahbar:</span> {application.supervisor?.full_name || "Tanlanmagan"}
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ariza qiymatlari</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {application.values.length === 0 ? (
              <p className="text-sm text-slate-500">Qiymatlar topilmadi.</p>
            ) : (
              application.values.map((value) => (
                <div key={value.id} className="rounded-md border border-slate-200 p-3">
                  <p className="text-sm font-semibold text-slate-900">
                    {value.column?.name || value.column_id}
                  </p>
                  {value.value_text && <p className="mt-1 text-sm text-slate-700">{value.value_text}</p>}
                  {value.value_file_url && (
                    <Link
                      href={value.value_file_url}
                      target="_blank"
                      className="mt-2 inline-block text-sm text-sky-700 underline"
                    >
                      Yuklangan faylni ochish
                    </Link>
                  )}
                  {(value.value_text || value.plagiarism_checked_at || (value.plagiarism_matches?.length ?? 0) > 0) && (
                    <PlagiarismSummary value={value} />
                  )}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <ScoringPanel application={application} />
    </div>
  )
}
