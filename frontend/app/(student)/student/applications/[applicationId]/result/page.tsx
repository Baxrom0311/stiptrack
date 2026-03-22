"use client"

import { useQuery } from "@tanstack/react-query"
import Link from "next/link"
import { useMemo } from "react"

import ApplicationStatusHistory from "@/components/application/ApplicationStatusHistory"
import ApplicationTimeline from "@/components/student/ApplicationTimeline"
import WinnerConfetti from "@/components/student/WinnerConfetti"
import { Badge } from "@/components/ui/badge"
import { buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import EmptyState from "@/components/ui/empty-state"
import { DetailPageSkeleton } from "@/components/ui/page-skeletons"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useApplication } from "@/hooks/useApplications"
import { listApplicationStatusLogs } from "@/lib/applications"
import { listVisibleEvaluations } from "@/lib/evaluations"
import { cn } from "@/lib/utils"
import type { ApplicationDetailResponse, ApplicationStatus, Column } from "@/types"

type StudentApplicationResultPageProps = {
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

function statusLabel(status: ApplicationStatus): string {
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
  if (status === "rejected") {
    return "Rad etilgan"
  }
  return status
}

function statusVariant(status: ApplicationStatus): "default" | "secondary" | "outline" | "destructive" {
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

function uniqueScorableColumns(application: ApplicationDetailResponse): Column[] {
  const scholarshipColumns = (application.scholarship?.columns ?? []).filter((column) => column.max_score > 0)
  if (scholarshipColumns.length > 0) {
    return scholarshipColumns
  }

  const seen = new Set<string>()
  const columns: Column[] = []
  for (const value of application.values) {
    if (!value.column || value.column.max_score <= 0 || seen.has(value.column.id)) {
      continue
    }
    seen.add(value.column.id)
    columns.push(value.column)
  }
  return columns
}

export default function StudentApplicationResultPage({ params }: StudentApplicationResultPageProps) {
  const applicationId = params.applicationId?.trim()

  const applicationQuery = useApplication(applicationId)
  const historyQuery = useQuery({
    queryKey: ["student-application-history", applicationId],
    queryFn: () => listApplicationStatusLogs(applicationId as string),
    enabled: Boolean(applicationId),
    retry: 0,
  })

  const evaluationsQuery = useQuery({
    queryKey: ["student-result-evaluations", applicationId],
    queryFn: () => listVisibleEvaluations(applicationId as string),
    enabled: Boolean(applicationId),
    retry: 0,
  })

  const columns = useMemo(
    () => (applicationQuery.data ? uniqueScorableColumns(applicationQuery.data) : []),
    [applicationQuery.data],
  )

  const columnRows = useMemo(() => {
    const evaluations = evaluationsQuery.data ?? []
    return columns.map((column) => {
      const scores = evaluations
        .map((evaluation) => evaluation.scores?.[column.id])
        .filter((score): score is number => typeof score === "number")
      const average = scores.length > 0 ? scores.reduce((acc, score) => acc + score, 0) / scores.length : null
      return {
        column,
        average,
        juryCount: scores.length,
      }
    })
  }, [columns, evaluationsQuery.data])

  const evaluationComments = useMemo(
    () =>
      (evaluationsQuery.data ?? []).filter(
        (evaluation) => typeof evaluation.final_comment === "string" && evaluation.final_comment.trim().length > 0,
      ),
    [evaluationsQuery.data],
  )

  if (!applicationId) {
    return null
  }

  if (applicationQuery.isLoading || evaluationsQuery.isLoading || historyQuery.isLoading) {
    return <DetailPageSkeleton className="xl:grid-cols-1" />
  }

  if (applicationQuery.isError || !applicationQuery.data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Natija topilmadi</CardTitle>
          <CardDescription>Ariza mavjud emas yoki sizda ko‘rish huquqi yo‘q.</CardDescription>
        </CardHeader>
        <CardContent>
          <Link className={cn(buttonVariants({ variant: "outline" }))} href="/student/applications">
            Orqaga qaytish
          </Link>
        </CardContent>
      </Card>
    )
  }

  const application = applicationQuery.data
  const isWinner = application.status === "winner"

  return (
    <div className="grid gap-6">
      <Card className="relative">
        {isWinner && <WinnerConfetti />}
        <CardHeader>
          <CardTitle>Ariza Natijasi</CardTitle>
          <CardDescription>{application.scholarship?.title ?? "Stipendiya"}</CardDescription>
        </CardHeader>
        <CardContent className="relative flex flex-col gap-4">
          {isWinner && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-emerald-900">
              <p className="text-lg font-semibold">Tabriklaymiz, siz g‘olib bo‘ldingiz!</p>
              <p className="mt-1 text-sm text-emerald-700">
                Yakuniy natija tasdiqlangan. Quyida mezonlar kesimida baholash tafsilotlari bor.
              </p>
            </div>
          )}
          <ApplicationTimeline status={application.status} />
          <div className="flex flex-wrap gap-2">
          <Badge variant={statusVariant(application.status)}>{statusLabel(application.status)}</Badge>
          <Badge variant="outline">Ariza ID: {application.id}</Badge>
          <Badge variant="secondary">
            Umumiy ball: {typeof application.total_score === "number" ? application.total_score.toFixed(2) : "-"}
          </Badge>
          <Badge variant="outline">
            Baholovchilar: {(evaluationsQuery.data ?? []).length}
          </Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Ustunlar Bo‘yicha Ballar</CardTitle>
          <CardDescription>Har bir mezon uchun o‘rtacha hakam bali ko‘rsatiladi.</CardDescription>
        </CardHeader>
        <CardContent>
          {columnRows.length === 0 ? (
            <EmptyState
              title="Baholash mezonlari topilmadi"
              description="Bu ariza uchun o‘rtacha ball ko‘rsatish mumkin bo‘lgan mezonlar hali shakllanmagan."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Mezon</TableHead>
                  <TableHead>Maksimal ball</TableHead>
                  <TableHead>O‘rtacha ball</TableHead>
                  <TableHead>Baholovchilar soni</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {columnRows.map(({ column, average, juryCount }) => (
                  <TableRow key={column.id}>
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="font-medium">{column.name}</span>
                        {column.description && <span className="text-xs text-slate-500">{column.description}</span>}
                      </div>
                    </TableCell>
                    <TableCell>{column.max_score.toFixed(2)}</TableCell>
                    <TableCell>{typeof average === "number" ? average.toFixed(2) : "-"}</TableCell>
                    <TableCell>{juryCount}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Hakim Tahlillari</CardTitle>
          <CardDescription>Topshirilgan baholashlar bo‘yicha yakuniy izohlar.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {evaluationComments.length === 0 ? (
            <EmptyState
              title="Hakam tahlili hali yo‘q"
              description="Baholovchilar yakuniy izohlarni topshirgandan keyin ular shu yerda ko‘rinadi."
            />
          ) : (
            evaluationComments.map((evaluation, index) => (
              <div key={evaluation.id ?? `${evaluation.application_id}-${index}`} className="rounded-md border p-4">
                <div className="mb-2 flex flex-wrap gap-2">
                  <Badge variant="outline">Baholash #{index + 1}</Badge>
                  <Badge variant="secondary">
                    Ball: {typeof evaluation.total_score === "number" ? evaluation.total_score.toFixed(2) : "-"}
                  </Badge>
                  <Badge variant="outline">Sana: {formatDate(evaluation.submitted_at)}</Badge>
                  {evaluation.ai_generated && <Badge>AI yordamida</Badge>}
                </div>
                <p className="text-sm text-slate-700">{evaluation.final_comment}</p>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <ApplicationStatusHistory
        logs={historyQuery.data ?? []}
        description="Arizaning qachon topshirilgani, review boshlangan va yakuniy holatlari shu yerda ko‘rinadi."
      />
    </div>
  )
}
