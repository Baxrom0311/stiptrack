"use client"

import { useQuery } from "@tanstack/react-query"
import { Download, FileSearch } from "lucide-react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { useEffect, useMemo, useState } from "react"

import { listScholarshipApplications } from "@/lib/applications"
import { listScholarships } from "@/lib/scholarships"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { buttonVariants, Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import EmptyState from "@/components/ui/empty-state"
import { Input } from "@/components/ui/input"
import { TableCardSkeleton } from "@/components/ui/page-skeletons"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { ApplicationListItem, ApplicationStatus } from "@/types"

type SortOption = "score_desc" | "score_asc" | "submitted_desc" | "submitted_asc" | "student_asc" | "scholarship_asc"

type AggregatedApplicationRow = {
  application: ApplicationListItem
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

function escapeCsv(value: string | number | null | undefined): string {
  const normalized = value == null ? "" : String(value)
  if (/[",\n]/.test(normalized)) {
    return `"${normalized.replace(/"/g, '""')}"`
  }
  return normalized
}

function downloadCsv(rows: AggregatedApplicationRow[]) {
  const headers = ["Application ID", "Scholarship", "Student", "Email", "Supervisor", "Status", "Score", "Submitted At"]
  const lines = rows.map(({ application }) => [
    application.id,
    application.scholarship?.title ?? "",
    application.student?.full_name ?? "",
    application.student?.email ?? "",
    application.supervisor_id ?? "",
    application.status,
    typeof application.total_score === "number" ? application.total_score.toFixed(2) : "",
    application.submitted_at ?? "",
  ])

  const csv = [headers, ...lines].map((line) => line.map((cell) => escapeCsv(cell)).join(",")).join("\n")
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = `admin-applications-${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export default function AdminApplicationsPage() {
  const searchParams = useSearchParams()
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | "all">("all")
  const [scholarshipFilter, setScholarshipFilter] = useState(searchParams.get("scholarshipId") ?? "all")
  const [sort, setSort] = useState<SortOption>("score_desc")

  useEffect(() => {
    setScholarshipFilter(searchParams.get("scholarshipId") ?? "all")
  }, [searchParams])

  const query = useQuery({
    queryKey: ["admin-applications-list"],
    queryFn: async (): Promise<AggregatedApplicationRow[]> => {
      const scholarships = await listScholarships({ limit: 200 })
      const applicationsByScholarship = await Promise.allSettled(
        scholarships.map((scholarship) => listScholarshipApplications(scholarship.id, { limit: 200 })),
      )

      const merged: ApplicationListItem[] = []
      for (const result of applicationsByScholarship) {
        if (result.status === "fulfilled") {
          merged.push(...result.value)
        }
      }

      const uniqueApplications = Array.from(new Map(merged.map((application) => [application.id, application])).values())
      return uniqueApplications.map((application) => ({ application }))
    },
    retry: 0,
  })

  const counts = useMemo(() => {
    const source = query.data ?? []
    return source.reduce(
      (acc, row) => {
        acc.all += 1
        acc[row.application.status] += 1
        return acc
      },
      { all: 0, draft: 0, submitted: 0, in_review: 0, winner: 0, rejected: 0 },
    )
  }, [query.data])

  const filteredRows = useMemo(() => {
    const source = [...(query.data ?? [])]
    const normalized = search.trim().toLowerCase()

    const filtered = source.filter((row) => {
      if (statusFilter !== "all" && row.application.status !== statusFilter) {
        return false
      }
      if (scholarshipFilter !== "all" && row.application.scholarship_id !== scholarshipFilter) {
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

    filtered.sort((left, right) => {
      if (sort === "score_asc") {
        return (left.application.total_score ?? -1) - (right.application.total_score ?? -1)
      }
      if (sort === "score_desc") {
        return (right.application.total_score ?? -1) - (left.application.total_score ?? -1)
      }
      if (sort === "submitted_asc") {
        return new Date(left.application.submitted_at ?? 0).getTime() - new Date(right.application.submitted_at ?? 0).getTime()
      }
      if (sort === "submitted_desc") {
        return new Date(right.application.submitted_at ?? 0).getTime() - new Date(left.application.submitted_at ?? 0).getTime()
      }
      if (sort === "student_asc") {
        return (left.application.student?.full_name ?? "").localeCompare(right.application.student?.full_name ?? "")
      }
      return (left.application.scholarship?.title ?? "").localeCompare(right.application.scholarship?.title ?? "")
    })

    return filtered
  }, [query.data, scholarshipFilter, search, sort, statusFilter])

  const scholarshipOptions = useMemo(() => {
    const source = query.data ?? []
    return Array.from(
      new Map(
        source
          .map((row) => row.application.scholarship)
          .filter((item): item is NonNullable<ApplicationListItem["scholarship"]> => Boolean(item))
          .map((scholarship) => [scholarship.id, scholarship]),
      ).values(),
    ).sort((left, right) => left.title.localeCompare(right.title))
  }, [query.data])

  const hasAnyRows = (query.data?.length ?? 0) > 0
  const hasActiveFilters = search.trim().length > 0 || statusFilter !== "all" || scholarshipFilter !== "all"

  if (query.isLoading) {
    return <TableCardSkeleton rows={8} columns={7} />
  }

  return (
    <div className="grid gap-6">
      <section className="rounded-3xl bg-[linear-gradient(135deg,_#fef3c7,_#fff7ed_45%,_#eff6ff)] p-6 ring-1 ring-amber-200">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <Badge variant="outline">Applications Control</Badge>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Admin arizalar ro‘yxati</h1>
            <p className="max-w-3xl text-sm text-slate-700">
              Barcha stipendiyalar bo‘yicha arizalarni bitta joyda ko‘ring, filterlang, saralang va CSV export qiling.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button type="button" variant="outline" onClick={() => downloadCsv(filteredRows)} disabled={filteredRows.length === 0}>
              <Download className="mr-2 h-4 w-4" />
              CSV export
            </Button>
          </div>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        <Card className="border-slate-200"><CardContent className="pt-6"><p className="text-xs uppercase text-slate-500">Barchasi</p><p className="mt-2 text-2xl font-semibold">{counts.all}</p></CardContent></Card>
        <Card className="border-slate-200"><CardContent className="pt-6"><p className="text-xs uppercase text-slate-500">Draft</p><p className="mt-2 text-2xl font-semibold">{counts.draft}</p></CardContent></Card>
        <Card className="border-slate-200"><CardContent className="pt-6"><p className="text-xs uppercase text-slate-500">Submitted</p><p className="mt-2 text-2xl font-semibold">{counts.submitted}</p></CardContent></Card>
        <Card className="border-slate-200"><CardContent className="pt-6"><p className="text-xs uppercase text-slate-500">Review</p><p className="mt-2 text-2xl font-semibold">{counts.in_review}</p></CardContent></Card>
        <Card className="border-slate-200"><CardContent className="pt-6"><p className="text-xs uppercase text-slate-500">Winner</p><p className="mt-2 text-2xl font-semibold">{counts.winner}</p></CardContent></Card>
        <Card className="border-slate-200"><CardContent className="pt-6"><p className="text-xs uppercase text-slate-500">Rejected</p><p className="mt-2 text-2xl font-semibold">{counts.rejected}</p></CardContent></Card>
      </div>

      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle>Filter va sort</CardTitle>
          <CardDescription>Scholarship, status, qidiruv va saralashni shu yerdan boshqaring.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 xl:grid-cols-[minmax(0,1.3fr)_220px_260px_220px]">
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Talaba, email, stipendiya yoki ariza ID bo‘yicha qidirish"
          />
          <select
            className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as ApplicationStatus | "all")}
          >
            <option value="all">Barcha statuslar</option>
            <option value="draft">Draft</option>
            <option value="submitted">Submitted</option>
            <option value="in_review">In review</option>
            <option value="winner">Winner</option>
            <option value="rejected">Rejected</option>
          </select>
          <select
            className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm"
            value={scholarshipFilter}
            onChange={(event) => setScholarshipFilter(event.target.value)}
          >
            <option value="all">Barcha stipendiyalar</option>
            {scholarshipOptions.map((scholarship) => (
              <option key={scholarship.id} value={scholarship.id}>
                {scholarship.title}
              </option>
            ))}
          </select>
          <select
            className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm"
            value={sort}
            onChange={(event) => setSort(event.target.value as SortOption)}
          >
            <option value="score_desc">Ball: yuqoridan</option>
            <option value="score_asc">Ball: pastdan</option>
            <option value="submitted_desc">Sana: yangi</option>
            <option value="submitted_asc">Sana: eski</option>
            <option value="student_asc">Talaba: A-Z</option>
            <option value="scholarship_asc">Stipendiya: A-Z</option>
          </select>
        </CardContent>
      </Card>

      {query.isError && (
        <Card className="border-red-200">
          <CardContent className="pt-6 text-sm text-red-700">Arizalarni yuklab bo‘lmadi. API va admin ruxsatlarini tekshiring.</CardContent>
        </Card>
      )}

      {!query.isError && filteredRows.length === 0 ? (
        <Card className="border-slate-200">
          <CardContent className="pt-6">
            <EmptyState
              title={hasAnyRows ? "Mos ariza topilmadi" : "Arizalar hali yo‘q"}
              description={
                hasAnyRows
                  ? "Qidiruv yoki filter shartlariga mos ariza chiqmagan. So‘rovni kengaytiring yoki filterlarni tozalang."
                  : "Studentlar ariza topshirgandan keyin ular shu sahifada paydo bo‘ladi."
              }
              action={
                hasActiveFilters ? (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setSearch("")
                      setStatusFilter("all")
                      setScholarshipFilter("all")
                      setSort("score_desc")
                    }}
                  >
                    Filterlarni tozalash
                  </Button>
                ) : undefined
              }
            />
          </CardContent>
        </Card>
      ) : null}

      {!query.isError && filteredRows.length > 0 && (
        <Card className="border-slate-200">
          <CardContent className="pt-6">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Talaba</TableHead>
                  <TableHead>Stipendiya</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Ball</TableHead>
                  <TableHead>Topshirilgan</TableHead>
                  <TableHead className="text-right">Amallar</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRows.map(({ application }) => (
                  <TableRow key={application.id}>
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="font-medium text-slate-900">{application.student?.full_name ?? "Noma’lum"}</span>
                        <span className="text-xs text-slate-500">{application.student?.email ?? application.id}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col">
                        <span>{application.scholarship?.title ?? "-"}</span>
                        <span className="text-xs text-slate-500">{application.scholarship_id}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusBadgeVariant(application.status)}>{applicationStatusLabel(application.status)}</Badge>
                    </TableCell>
                    <TableCell>{typeof application.total_score === "number" ? application.total_score.toFixed(2) : "-"}</TableCell>
                    <TableCell>{formatDate(application.submitted_at)}</TableCell>
                    <TableCell className="text-right">
                      <Link href={`/admin/applications/${application.id}`} className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
                        <FileSearch className="mr-2 h-4 w-4" />
                        Detail
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
