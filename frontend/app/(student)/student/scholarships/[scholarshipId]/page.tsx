"use client"

import Link from "next/link"
import { useMemo } from "react"

import StatusBadge from "@/components/scholarship/StatusBadge"
import { Badge } from "@/components/ui/badge"
import { buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import EmptyState from "@/components/ui/empty-state"
import { DetailPageSkeleton } from "@/components/ui/page-skeletons"
import { useMyApplications } from "@/hooks/useApplications"
import { useScholarship, useScholarshipColumns } from "@/hooks/useScholarships"
import { cn } from "@/lib/utils"
import type { ApplicationListItem, Column } from "@/types"

type StudentScholarshipDetailPageProps = {
  params: {
    scholarshipId: string
  }
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

function fieldTypeLabel(value: Column["field_type"]): string {
  if (value === "textarea") {
    return "Textarea"
  }
  if (value === "file") {
    return "File"
  }
  if (value === "number") {
    return "Number"
  }
  if (value === "date") {
    return "Date"
  }
  if (value === "select") {
    return "Select"
  }
  if (value === "url") {
    return "URL"
  }
  return "Text"
}

function findApplication(applicationList: ApplicationListItem[], scholarshipId: string): ApplicationListItem | undefined {
  return applicationList.find((item) => item.scholarship_id === scholarshipId)
}

export default function StudentScholarshipDetailPage({ params }: StudentScholarshipDetailPageProps) {
  const scholarshipId = params.scholarshipId?.trim()
  const scholarshipQuery = useScholarship(scholarshipId)
  const columnsQuery = useScholarshipColumns(scholarshipId)
  const applicationsQuery = useMyApplications()

  const application = useMemo(() => {
    if (!scholarshipId) {
      return undefined
    }
    return findApplication(applicationsQuery.data ?? [], scholarshipId)
  }, [applicationsQuery.data, scholarshipId])

  if (!scholarshipId) {
    return null
  }

  if (scholarshipQuery.isLoading || columnsQuery.isLoading || applicationsQuery.isLoading) {
    return <DetailPageSkeleton className="xl:grid-cols-[1.2fr_0.9fr]" />
  }

  if (scholarshipQuery.isError || !scholarshipQuery.data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Stipendiya topilmadi</CardTitle>
          <CardDescription>Bu stipendiya mavjud emas yoki o‘chirilgan.</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  const scholarship = scholarshipQuery.data
  const columns = columnsQuery.data ?? scholarship.columns ?? []
  const primaryHref = application
    ? application.status === "draft"
      ? "/student/scholarships/" + scholarship.id + "/apply"
      : "/student/applications/" + application.id + "/result"
    : "/student/scholarships/" + scholarship.id + "/apply"
  const primaryLabel = application
    ? application.status === "draft"
      ? "Qoralamani davom ettirish"
      : "Natijani ko‘rish"
    : "Ariza topshirish"

  return (
    <div className="grid gap-6 xl:grid-cols-[1.2fr_0.9fr]">
      <div className="space-y-6">
        <section className="rounded-3xl bg-[linear-gradient(135deg,_#eff6ff,_#f0fdf4_55%,_#f8fafc)] p-6 ring-1 ring-sky-200">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={scholarship.status} />
              {scholarship.ai_analysis_enabled && <Badge variant="outline">AI enabled</Badge>}
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-900">{scholarship.title}</h1>
            <p className="max-w-3xl text-sm text-slate-600">{scholarship.description || "Tavsif ko‘rsatilmagan."}</p>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Badge variant="secondary">Deadline: {formatDeadline(scholarship.deadline)}</Badge>
            <Badge variant="outline">Winners: {scholarship.max_winners}</Badge>
            <Badge variant="outline">Columns: {columns.length}</Badge>
          </div>
        </section>

        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle>Baholash va forma ustunlari</CardTitle>
            <CardDescription>Ariza topshirishda shu maydonlar dinamik shaklda ko‘rinadi.</CardDescription>
          </CardHeader>
          <CardContent>
            {columns.length === 0 ? (
              <EmptyState
                title="Ustunlar hali tayyor emas"
                description="Admin bu stipendiya uchun forma maydonlarini hali yaratmagan."
              />
            ) : (
              <div className="grid gap-3">
                {columns.map((column) => (
                  <div key={column.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-slate-900">{column.name}</p>
                      <Badge variant="outline">{fieldTypeLabel(column.field_type)}</Badge>
                      {column.is_required && <Badge variant="secondary">Majburiy</Badge>}
                      {column.ai_analyze && <Badge variant="outline">AI analyze</Badge>}
                      <Badge variant="outline">Max score: {column.max_score}</Badge>
                    </div>
                    {column.description && <p className="mt-2 text-sm text-slate-600">{column.description}</p>}
                    {column.select_options?.length ? (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {column.select_options.map((option) => (
                          <Badge key={option} variant="outline">
                            {option}
                          </Badge>
                        ))}
                      </div>
                    ) : null}
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
            <CardTitle>Ariza holati</CardTitle>
            <CardDescription>Bu stipendiya bo‘yicha sizning hozirgi oqimingiz.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {application ? (
              <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">
                <p className="font-medium text-slate-900">Joriy ariza</p>
                <p className="mt-1">Holat: {application.status}</p>
                <p className="mt-1">Umumiy ball: {typeof application.total_score === "number" ? application.total_score.toFixed(2) : "-"}</p>
              </div>
            ) : (
              <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">
                Siz hali bu stipendiyaga ariza topshirmagansiz.
              </div>
            )}

            <div className="flex flex-col gap-3">
              <Link href={primaryHref} className={cn(buttonVariants({ variant: "outline" }), "w-full")}>
                {primaryLabel}
              </Link>
              <Link href="/student/scholarships" className={cn(buttonVariants({ variant: "outline" }), "w-full")}>
                Ochiq stipendiyalarga qaytish
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
