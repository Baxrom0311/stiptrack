"use client"

import { useQuery } from "@tanstack/react-query"
import Link from "next/link"
import { useMemo } from "react"
import { History } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import EmptyState from "@/components/ui/empty-state"
import { ListCardsSkeleton, StatCardsSkeleton } from "@/components/ui/page-skeletons"
import { useMyApplications } from "@/hooks/useApplications"
import { listScholarships } from "@/lib/scholarships"
import { cn } from "@/lib/utils"
import type { ApplicationListItem, ApplicationStatus } from "@/types"

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

function latestItems(applications: ApplicationListItem[]): ApplicationListItem[] {
  return [...applications]
    .sort((a, b) => {
      const ad = new Date(a.updated_at ?? a.submitted_at ?? a.created_at ?? 0).getTime()
      const bd = new Date(b.updated_at ?? b.submitted_at ?? b.created_at ?? 0).getTime()
      return bd - ad
    })
    .slice(0, 5)
}

export default function StudentDashboardPage() {
  const applicationsQuery = useMyApplications()

  const scholarshipsQuery = useQuery({
    queryKey: ["student-dashboard-open-scholarships"],
    queryFn: () => listScholarships({ status: "open", limit: 100 }),
    retry: 0,
  })

  const stats = useMemo(() => {
    const applications = applicationsQuery.data ?? []
    const activeItems = applications.filter(
      (item) => item.status === "draft" || item.status === "submitted" || item.status === "in_review",
    )
    const completedItems = applications.filter(
      (item) => item.status === "winner" || item.status === "rejected",
    )
    const activeApplications = applications.filter((item) =>
      item.status === "submitted" || item.status === "in_review",
    ).length
    const completedResults = completedItems.length
    const wonCount = applications.filter((item) => item.status === "winner").length

    return {
      activeApplications,
      completedResults,
      openScholarships: (scholarshipsQuery.data ?? []).length,
      wonCount,
      latestApplications: latestItems(activeItems),
      completedHistory: latestItems(completedItems),
    }
  }, [applicationsQuery.data, scholarshipsQuery.data])

  if (applicationsQuery.isLoading || scholarshipsQuery.isLoading) {
    return (
      <div className="grid gap-6">
        <StatCardsSkeleton />
        <ListCardsSkeleton count={4} />
      </div>
    )
  }

  return (
    <div className="grid gap-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="border-sky-100 bg-sky-50">
          <CardHeader>
            <CardTitle className="text-sm">Faol Arizalar</CardTitle>
            <CardDescription>Ko‘rib chiqish jarayonida</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold text-sky-900">{stats.activeApplications}</p>
          </CardContent>
        </Card>

        <Card className="border-violet-100 bg-violet-50">
          <CardHeader>
            <CardTitle className="text-sm">Yakunlangan Natijalar</CardTitle>
            <CardDescription>E’lon qilingan arizalar</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold text-violet-900">{stats.completedResults}</p>
          </CardContent>
        </Card>

        <Card className="border-emerald-100 bg-emerald-50">
          <CardHeader>
            <CardTitle className="text-sm">Yangi Stipendiyalar</CardTitle>
            <CardDescription>Hozir ochiq bo‘lganlari</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold text-emerald-900">{stats.openScholarships}</p>
          </CardContent>
        </Card>

        <Card className="border-amber-100 bg-amber-50">
          <CardHeader>
            <CardTitle className="text-sm">G‘olibliklar</CardTitle>
            <CardDescription>Siz yutgan stipendiyalar</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold text-amber-900">{stats.wonCount}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Faol Jarayonlar</CardTitle>
          <CardDescription>Hozir davom etayotgan arizalar holati</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {(applicationsQuery.isError || scholarshipsQuery.isError) && (
            <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
              Dashboardni yuklab bo‘lmadi. Tizimga qayta kirib yana urinib ko‘ring.
            </div>
          )}

          {!applicationsQuery.isLoading &&
            !applicationsQuery.isError &&
            stats.latestApplications.length === 0 && (
              <EmptyState
                title="Faol ariza yo‘q"
                description="Hozir ko‘rib chiqilayotgan yoki qoralama holatdagi arizalar topilmadi. Yangi ochiq stipendiyalarga topshirish mumkin."
                action={
                  <Link
                    href="/student/scholarships"
                    className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                  >
                    Ochiq stipendiyalar
                  </Link>
                }
              />
            )}

          {stats.latestApplications.map((application) => (
            <div
              key={application.id}
              className="flex flex-col gap-3 rounded-lg border border-slate-200 p-4 md:flex-row md:items-center md:justify-between"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-900">
                  {application.scholarship?.title ?? "Stipendiya"}
                </p>
                <p className="text-xs text-slate-500">Topshirilgan: {formatDate(application.submitted_at)}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={statusVariant(application.status)}>{statusLabel(application.status)}</Badge>
                <Badge variant="outline">
                  Ball: {typeof application.total_score === "number" ? application.total_score.toFixed(2) : "-"}
                </Badge>
                <Link
                  href={`/student/applications/${application.id}/result`}
                  className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                >
                  Natijani ko‘rish
                </Link>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Yakunlangan Stipendiyalar Tarixi</CardTitle>
          <CardDescription>Natijasi e’lon qilingan arizalar arxivi</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {!applicationsQuery.isLoading &&
            !applicationsQuery.isError &&
            stats.completedHistory.length === 0 && (
              <EmptyState
                icon={History}
                title="Yakunlangan tarix hali yo‘q"
                description="G‘olib yoki rad etilgan arizalar shu blokda saqlanadi. Natijalar e’lon qilingach tarix shakllanadi."
              />
            )}

          {stats.completedHistory.map((application) => (
            <div
              key={application.id}
              className="flex flex-col gap-3 rounded-lg border border-slate-200 p-4 md:flex-row md:items-center md:justify-between"
            >
              <div className="min-w-0 space-y-1">
                <p className="truncate text-sm font-semibold text-slate-900">
                  {application.scholarship?.title ?? "Stipendiya"}
                </p>
                <p className="text-xs text-slate-500">
                  Yakunlangan: {formatDate(application.updated_at ?? application.submitted_at)}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={statusVariant(application.status)}>{statusLabel(application.status)}</Badge>
                <Badge variant="outline">
                  Ball: {typeof application.total_score === "number" ? application.total_score.toFixed(2) : "-"}
                </Badge>
                <Link
                  href={`/student/applications/${application.id}/result`}
                  className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                >
                  Tarix/Natija
                </Link>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
