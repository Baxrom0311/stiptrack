"use client"

import { useQuery } from "@tanstack/react-query"
import Link from "next/link"
import { useMemo, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { buttonVariants, Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import EmptyState from "@/components/ui/empty-state"
import { Input } from "@/components/ui/input"
import { TableCardSkeleton } from "@/components/ui/page-skeletons"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { listScholarshipApplications } from "@/lib/applications"
import { getEvaluation } from "@/lib/evaluations"
import { listScholarships } from "@/lib/scholarships"
import { cn } from "@/lib/utils"
import type { ApplicationListItem, Evaluation } from "@/types"

type EvaluationFilter = "all" | "unscored" | "scored" | "submitted"

type JuryApplicationRow = {
  application: ApplicationListItem
  evaluation: Evaluation
  evaluationState: Exclude<EvaluationFilter, "all">
}

function normalizeEvaluation(applicationId: string, evaluation: Evaluation | null): Evaluation {
  if (evaluation) {
    return evaluation
  }
  return {
    id: null,
    application_id: applicationId,
    jury_id: "",
    scores: {},
    total_score: null,
    final_comment: null,
    ai_generated: false,
    is_submitted: false,
    submitted_at: null,
  }
}

function resolveEvaluationState(evaluation: Evaluation): Exclude<EvaluationFilter, "all"> {
  if (evaluation.is_submitted) {
    return "submitted"
  }
  if (evaluation.id || Object.keys(evaluation.scores ?? {}).length > 0) {
    return "scored"
  }
  return "unscored"
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

function applicationStatusLabel(status: string): string {
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

function statusBadgeVariant(status: string): "default" | "secondary" | "outline" | "destructive" {
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

function evaluationLabel(state: Exclude<EvaluationFilter, "all">): string {
  if (state === "unscored") {
    return "Baholanmagan"
  }
  if (state === "scored") {
    return "Baholangan"
  }
  return "Topshirilgan"
}

function participantName(application: ApplicationListItem): string {
  if (application.student?.full_name) {
    return application.student.full_name
  }
  if (application.scholarship?.blind_review_enabled) {
    return `Anonim ishtirokchi #${application.id.slice(0, 8)}`
  }
  return "Noma’lum"
}

function participantSubtitle(application: ApplicationListItem): string {
  if (application.student?.email) {
    return application.student.email
  }
  if (application.scholarship?.blind_review_enabled) {
    return "Blind review yoqilgan"
  }
  return "-"
}

export default function JuryApplicationsPage() {
  const [search, setSearch] = useState("")
  const [filter, setFilter] = useState<EvaluationFilter>("all")

  const query = useQuery({
    queryKey: ["jury-applications-list"],
    queryFn: async (): Promise<JuryApplicationRow[]> => {
      const scholarships = await listScholarships({ limit: 100 })
      const applicationsByScholarship = await Promise.allSettled(
        scholarships.map((scholarship) => listScholarshipApplications(scholarship.id, { limit: 200 })),
      )

      const merged: ApplicationListItem[] = []
      for (const result of applicationsByScholarship) {
        if (result.status === "fulfilled") {
          merged.push(...result.value)
        }
      }

      const uniqueApplications = Array.from(
        new Map(
          merged
            .filter((application) => application.status !== "draft")
            .map((application) => [application.id, application]),
        ).values(),
      )

      const evaluations = await Promise.allSettled(
        uniqueApplications.map((application) => getEvaluation(application.id)),
      )

      return uniqueApplications.map((application, index) => {
        const evaluationResult = evaluations[index]
        const evaluation =
          evaluationResult.status === "fulfilled"
            ? normalizeEvaluation(application.id, evaluationResult.value)
            : normalizeEvaluation(application.id, null)

        return {
          application,
          evaluation,
          evaluationState: resolveEvaluationState(evaluation),
        }
      })
    },
    retry: 0,
  })

  const counts = useMemo(() => {
    const source = query.data ?? []
    return source.reduce(
      (acc, row) => {
        acc.all += 1
        acc[row.evaluationState] += 1
        return acc
      },
      { all: 0, unscored: 0, scored: 0, submitted: 0 },
    )
  }, [query.data])

  const filteredRows = useMemo(() => {
    const source = query.data ?? []
    const normalized = search.trim().toLowerCase()

    return source.filter((row) => {
      if (filter !== "all" && row.evaluationState !== filter) {
        return false
      }

      if (!normalized) {
        return true
      }

      const haystack = [
        row.application.id,
        row.application.student?.full_name,
        row.application.student?.email,
        row.application.scholarship?.title,
      ]
        .filter((item): item is string => Boolean(item))
        .join(" ")
        .toLowerCase()

      return haystack.includes(normalized)
    })
  }, [filter, query.data, search])
  const hasAnyRows = (query.data?.length ?? 0) > 0
  const hasActiveFilters = filter !== "all" || search.trim().length > 0

  if (query.isLoading) {
    return <TableCardSkeleton rows={6} columns={6} />
  }

  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Hakim Arizalar Ro‘yxati</CardTitle>
          <CardDescription>
            Sizga tegishli arizalarni baholash holati bo‘yicha boshqaring va detail sahifaga o‘ting.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button
              variant={filter === "all" ? "default" : "outline"}
              onClick={() => setFilter("all")}
              type="button"
            >
              Barchasi ({counts.all})
            </Button>
            <Button
              variant={filter === "unscored" ? "default" : "outline"}
              onClick={() => setFilter("unscored")}
              type="button"
            >
              Baholanmagan ({counts.unscored})
            </Button>
            <Button
              variant={filter === "scored" ? "default" : "outline"}
              onClick={() => setFilter("scored")}
              type="button"
            >
              Baholangan ({counts.scored})
            </Button>
            <Button
              variant={filter === "submitted" ? "default" : "outline"}
              onClick={() => setFilter("submitted")}
              type="button"
            >
              Topshirilgan ({counts.submitted})
            </Button>
          </div>

          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Ishtirokchi, stipendiya yoki ariza ID bo‘yicha qidirish"
          />

          {query.isError && (
            <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
              Arizalarni yuklab bo‘lmadi. API va ruxsatlarni tekshiring.
            </div>
          )}

          {!query.isLoading && !query.isError && filteredRows.length === 0 && (
            <EmptyState
              title={hasAnyRows ? "Mos ariza topilmadi" : "Baholash uchun arizalar yo‘q"}
              description={
                hasAnyRows
                  ? "Qidiruv yoki filter shartlariga mos ariza chiqmagan. So‘rovni kengaytiring yoki filterlarni tozalang."
                  : "Sizga biriktirilgan stipendiyalar bo‘yicha arizalar shu yerda paydo bo‘ladi."
              }
              action={
                hasActiveFilters ? (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setSearch("")
                      setFilter("all")
                    }}
                  >
                    Filterlarni tozalash
                  </Button>
                ) : undefined
              }
            />
          )}

          {!query.isLoading && !query.isError && filteredRows.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ishtirokchi</TableHead>
                  <TableHead>Stipendiya</TableHead>
                  <TableHead>Ariza holati</TableHead>
                  <TableHead>Baholash holati</TableHead>
                  <TableHead>Ball</TableHead>
                  <TableHead>Topshirilgan sana</TableHead>
                  <TableHead className="text-right">Amallar</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRows.map((row) => (
                  <TableRow key={row.application.id}>
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="font-medium">{participantName(row.application)}</span>
                        <span className="text-xs text-slate-500">{participantSubtitle(row.application)}</span>
                      </div>
                    </TableCell>
                    <TableCell>{row.application.scholarship?.title ?? "-"}</TableCell>
                    <TableCell>
                      <Badge variant={statusBadgeVariant(row.application.status)}>
                        {applicationStatusLabel(row.application.status)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={row.evaluationState === "submitted" ? "default" : "outline"}>
                        {evaluationLabel(row.evaluationState)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {typeof row.evaluation.total_score === "number"
                        ? row.evaluation.total_score.toFixed(2)
                        : "-"}
                    </TableCell>
                    <TableCell>{formatDate(row.application.submitted_at)}</TableCell>
                    <TableCell className="text-right">
                      <Link
                        href={`/jury/applications/${row.application.id}`}
                        className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                      >
                        Ochish
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
