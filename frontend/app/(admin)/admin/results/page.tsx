"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Award, BarChart3, Download, FileSpreadsheet, Trophy } from "lucide-react"
import { useEffect, useMemo, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import EmptyState from "@/components/ui/empty-state"
import { HeroSkeleton, StatCardsSkeleton, TableCardSkeleton } from "@/components/ui/page-skeletons"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { announceWinners, downloadScholarshipResultsExport, getScholarshipResults } from "@/lib/admin"
import { notifyError, notifySuccess } from "@/lib/notifications"
import { listScholarships } from "@/lib/scholarships"
import type { ApplicationStatus, EvaluationConsistencySummary, ScholarshipResultRow } from "@/types"

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
    return "Draft"
  }
  if (status === "submitted") {
    return "Submitted"
  }
  if (status === "in_review") {
    return "In Review"
  }
  if (status === "winner") {
    return "Winner"
  }
  if (status === "rejected") {
    return "Rejected"
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

function isRankedRow(row: ScholarshipResultRow): boolean {
  return typeof row.rank === "number" && typeof row.total_score === "number"
}

function consistencyLabel(consistency?: EvaluationConsistencySummary | null): string {
  if (!consistency || consistency.jury_count === 0) {
    return "No reviews"
  }
  if (consistency.jury_count === 1 || typeof consistency.score_spread !== "number") {
    return `${consistency.jury_count} hakam`
  }
  return `Spread: ${consistency.score_spread.toFixed(2)}`
}

function consistencyDescription(consistency?: EvaluationConsistencySummary | null): string {
  if (!consistency || consistency.jury_count === 0) {
    return "Hali submitted baho yo‘q"
  }
  if (consistency.jury_count === 1) {
    return "Kamida 2 hakam kerak"
  }
  return `Avg ${consistency.average_score?.toFixed(2) ?? "-"} | Std ${consistency.score_stddev?.toFixed(2) ?? "-"}`
}

function consistencyVariant(
  consistency?: EvaluationConsistencySummary | null,
): "default" | "secondary" | "outline" | "destructive" {
  if (!consistency || consistency.jury_count === 0) {
    return "outline"
  }
  if (consistency.is_flagged) {
    return "destructive"
  }
  if (consistency.jury_count >= 2) {
    return "secondary"
  }
  return "outline"
}

export default function AdminResultsPage() {
  const queryClient = useQueryClient()
  const [selectedScholarshipId, setSelectedScholarshipId] = useState("")
  const [announceOpen, setAnnounceOpen] = useState(false)
  const [exportingFormat, setExportingFormat] = useState<"xlsx" | "pdf" | null>(null)

  const scholarshipsQuery = useQuery({
    queryKey: ["admin-results-scholarships"],
    queryFn: () => listScholarships({ limit: 200 }),
    retry: 0,
  })

  const resultsQuery = useQuery({
    queryKey: ["admin-results-detail", selectedScholarshipId],
    queryFn: () => getScholarshipResults(selectedScholarshipId),
    enabled: Boolean(selectedScholarshipId),
    retry: 0,
  })

  const announceMutation = useMutation({
    mutationFn: () => announceWinners(selectedScholarshipId),
    onSuccess: async (result) => {
      notifySuccess(result.detail)
      await queryClient.invalidateQueries({ queryKey: ["admin-results-detail", selectedScholarshipId] })
      await queryClient.invalidateQueries({ queryKey: ["admin-results-scholarships"] })
    },
    onError: (error) => {
      notifyError(error)
    },
  })

  const topRows = useMemo(() => {
    const rows = resultsQuery.data?.rows ?? []
    return rows
      .filter(isRankedRow)
      .sort((a, b) => {
        const scoreA = a.total_score ?? -1
        const scoreB = b.total_score ?? -1
        return scoreB - scoreA
      })
      .slice(0, resultsQuery.data?.max_winners ?? 0)
  }, [resultsQuery.data])

  const allRows = useMemo(() => resultsQuery.data?.rows ?? [], [resultsQuery.data])
  const results = resultsQuery.data
  const flaggedRowsCount = useMemo(
    () => allRows.filter((row) => row.consistency?.is_flagged).length,
    [allRows],
  )
  const announceWarnings = useMemo(() => {
    if (!results) {
      return []
    }

    const warnings: string[] = []
    if (results.scholarship_status !== "closed") {
      warnings.push("G‘oliblarni e’lon qilish odatda faqat `closed` holatdagi stipendiya uchun ishlatiladi.")
    }
    if (topRows.length < results.max_winners) {
      warnings.push("Top-N preview winner slotlaridan kam. Tasdiqda mavjud nomzodlargina winner bo‘ladi.")
    }
    if (results.winners_count > 0) {
      warnings.push("Bu stipendiyada allaqachon winner statusidagi arizalar bor. Tasdiq winner holatlarini qayta hisoblaydi.")
    }
    return warnings
  }, [results, topRows.length])

  const canAnnounce =
    results?.scholarship_status === "closed" &&
    !announceMutation.isPending &&
    topRows.length > 0

  const canExport = Boolean(results) && !resultsQuery.isLoading && !exportingFormat

  async function handleExport(format: "xlsx" | "pdf") {
    if (!selectedScholarshipId) {
      return
    }

    try {
      setExportingFormat(format)
      await downloadScholarshipResultsExport(selectedScholarshipId, format)
    } catch (error) {
      notifyError(error, `${format.toUpperCase()} eksportni yuklab bo'lmadi.`)
    } finally {
      setExportingFormat(null)
    }
  }

  useEffect(() => {
    setAnnounceOpen(false)
  }, [selectedScholarshipId])

  if (scholarshipsQuery.isLoading) {
    return (
      <div className="grid gap-6">
        <HeroSkeleton />
        <TableCardSkeleton rows={4} columns={4} withToolbar={false} />
      </div>
    )
  }

  if (selectedScholarshipId && resultsQuery.isLoading) {
    return (
      <div className="grid gap-6">
        <HeroSkeleton />
        <StatCardsSkeleton count={3} />
        <TableCardSkeleton rows={4} columns={4} withToolbar={false} />
        <TableCardSkeleton rows={6} columns={6} withToolbar={false} />
      </div>
    )
  }

  return (
    <div className="grid gap-6">
      <section className="rounded-3xl bg-[linear-gradient(135deg,_#f8fafc,_#e0f2fe_45%,_#ecfeff)] p-6 ring-1 ring-slate-200">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <Badge variant="outline">Final Results</Badge>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Stipendiya yakuniy natijalari</h1>
            <p className="max-w-2xl text-sm text-slate-600">
              Scholarship tanlang, rankingni ko‘ring va final qarorni tasdiqlang.
            </p>
          </div>

          <div className="w-full max-w-xl rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm">
            <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="results-scholarship">
              Scholarship
            </label>
            <select
              id="results-scholarship"
              className="h-10 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
              value={selectedScholarshipId}
              onChange={(event) => setSelectedScholarshipId(event.target.value)}
            >
              <option value="">Tanlang...</option>
              {(scholarshipsQuery.data ?? []).map((scholarship) => (
                <option key={scholarship.id} value={scholarship.id}>
                  {scholarship.title} ({scholarship.status})
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>
      {scholarshipsQuery.isError && (
        <Card>
          <CardHeader>
            <CardTitle>Scholarship ro‘yxatini yuklab bo‘lmadi</CardTitle>
          </CardHeader>
        </Card>
      )}

      {!selectedScholarshipId && (
        <Card>
          <CardHeader>
            <CardTitle>Natija ko‘rish uchun scholarship tanlang</CardTitle>
            <CardDescription>
              Yuqoridagi ro‘yxatdan bir scholarship tanlansa, ranking va winner preview chiqadi.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {resultsQuery.isError && selectedScholarshipId && (
        <Card>
          <CardHeader>
            <CardTitle>Natijalarni yuklab bo‘lmadi</CardTitle>
            <CardDescription>
              Scholarship uchun ranking hali tayyor emas yoki server xatoligi yuz berdi.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {results && (
        <>
          <div className="grid gap-4 xl:grid-cols-4">
            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <BarChart3 className="h-4 w-4 text-sky-600" />
                  Ranking Pool
                </CardTitle>
                <CardDescription>{results.scholarship_title}</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-semibold text-slate-900">{allRows.filter(isRankedRow).length}</p>
                <p className="mt-1 text-xs text-slate-500">Ballga ega nomzodlar soni</p>
              </CardContent>
            </Card>

            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Award className="h-4 w-4 text-amber-600" />
                  Winner Slots
                </CardTitle>
                <CardDescription>Stipendiya bo‘yicha limit</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-semibold text-slate-900">{results.max_winners}</p>
                <p className="mt-1 text-xs text-slate-500">Tasdiqlanadigan maksimal o‘rin</p>
              </CardContent>
            </Card>

            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Trophy className="h-4 w-4 text-emerald-600" />
                  Current Winners
                </CardTitle>
                <CardDescription>Hozirgi winner statusidagi arizalar</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-semibold text-slate-900">{results.winners_count}</p>
                <p className="mt-1 text-xs text-slate-500">Scholarship status: {results.scholarship_status}</p>
              </CardContent>
            </Card>

            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <BarChart3 className="h-4 w-4 text-rose-600" />
                  Consistency Flags
                </CardTitle>
                <CardDescription>Hakamlar ball farqi yuqori arizalar</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-semibold text-slate-900">{flaggedRowsCount}</p>
                <p className="mt-1 text-xs text-slate-500">
                  Threshold: {allRows.find((row) => row.consistency)?.consistency?.warning_threshold ?? 15} ball
                </p>
              </CardContent>
            </Card>
          </div>

          <Card className="border-slate-200">
            <CardHeader>
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <CardTitle>Winner Confirmation</CardTitle>
                  <CardDescription>
                    Top-{results.max_winners} ranking preview asosida g‘oliblarni tasdiqlang.
                  </CardDescription>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => handleExport("xlsx")}
                    disabled={!canExport}
                  >
                    <FileSpreadsheet className="mr-2 h-4 w-4" />
                    {exportingFormat === "xlsx" ? "Excel tayyorlanmoqda..." : "Excel export"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => handleExport("pdf")}
                    disabled={!canExport}
                  >
                    <Download className="mr-2 h-4 w-4" />
                    {exportingFormat === "pdf" ? "PDF tayyorlanmoqda..." : "PDF export"}
                  </Button>
                  <Button
                    type="button"
                    onClick={() => setAnnounceOpen(true)}
                    disabled={!canAnnounce}
                  >
                    G‘oliblarni tasdiqlash
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {results.scholarship_status === "done" && (
                <div className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                  Scholarship yakunlangan. Winnerlar allaqachon e’lon qilingan.
                </div>
              )}
              {results.scholarship_status !== "closed" && results.scholarship_status !== "done" && (
                <div className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  Winner tasdiqlash odatda `closed` holatdagi scholarship uchun ishlaydi.
                </div>
              )}

              {topRows.length === 0 ? (
                <EmptyState
                  title="Winner preview hali tayyor emas"
                  description="Top-N preview chiqishi uchun kamida bir nechta ariza baholanib, umumiy ball shakllanishi kerak."
                />
              ) : (
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {topRows.map((row, index) => (
                    <div key={row.application_id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                      <div className="mb-2 flex items-center justify-between">
                        <Badge>{`#${row.rank ?? index + 1}`}</Badge>
                        <Badge variant={row.is_winner ? "default" : "outline"}>
                          {row.is_winner ? "Winner" : "Preview"}
                        </Badge>
                      </div>
                      <p className="text-sm font-semibold text-slate-900">{row.student_name}</p>
                      <p className="mt-1 text-xs text-slate-500">Ariza ID: {row.application_id}</p>
                      <p className="mt-3 text-2xl font-semibold text-slate-900">
                        {typeof row.total_score === "number" ? row.total_score.toFixed(2) : "-"}
                      </p>
                      <p className="text-xs text-slate-500">Umumiy score</p>
                      <div className="mt-3 flex items-center justify-between gap-2">
                        <Badge variant={consistencyVariant(row.consistency)}>{consistencyLabel(row.consistency)}</Badge>
                        <span className="text-[11px] text-slate-500">{consistencyDescription(row.consistency)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Dialog open={announceOpen} onOpenChange={setAnnounceOpen}>
            <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
              <DialogHeader>
                <DialogTitle>G‘oliblarni e’lon qilish</DialogTitle>
                <DialogDescription>
                  Top-{results.max_winners} ranking preview asosida yakuniy winner statuslarini tasdiqlaysiz.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                      <p className="font-semibold text-slate-900">{results.scholarship_title}</p>
                      <p className="mt-1 text-sm text-slate-500">Scholarship ID: {results.scholarship_id}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="outline">Status: {results.scholarship_status}</Badge>
                      <Badge variant="outline">Winner slots: {results.max_winners}</Badge>
                      <Badge variant="outline">Current winners: {results.winners_count}</Badge>
                    </div>
                  </div>
                </div>

                {announceWarnings.length > 0 && (
                  <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                    <p className="font-medium">Ogohlantirishlar</p>
                    <ul className="mt-2 list-disc space-y-1 pl-5">
                      {announceWarnings.map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {topRows.length === 0 ? (
                  <EmptyState
                    title="Winner preview tayyor emas"
                    description="Tasdiqlashdan oldin kamida bitta baholangan ariza bo‘lishi kerak."
                  />
                ) : (
                  <div className="space-y-3">
                    <p className="text-sm font-medium text-slate-900">Tasdiqlanadigan winner preview</p>
                    <div className="overflow-hidden rounded-2xl border border-slate-200">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Rank</TableHead>
                            <TableHead>Student</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Score</TableHead>
                            <TableHead>Consistency</TableHead>
                            <TableHead>Submitted</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {topRows.map((row) => (
                            <TableRow key={row.application_id}>
                              <TableCell>{row.rank ?? "-"}</TableCell>
                              <TableCell>
                                <div className="flex flex-col">
                                  <span className="font-medium text-slate-900">{row.student_name}</span>
                                  <span className="text-xs text-slate-500">{row.application_id}</span>
                                </div>
                              </TableCell>
                              <TableCell>
                                <Badge variant={statusVariant(row.status)}>{statusLabel(row.status)}</Badge>
                              </TableCell>
                              <TableCell>{typeof row.total_score === "number" ? row.total_score.toFixed(2) : "-"}</TableCell>
                              <TableCell>
                                <Badge variant={consistencyVariant(row.consistency)}>{consistencyLabel(row.consistency)}</Badge>
                              </TableCell>
                              <TableCell>{formatDate(row.submitted_at)}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                )}
              </div>

              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setAnnounceOpen(false)}>
                  Bekor qilish
                </Button>
                <Button
                  type="button"
                  onClick={() =>
                    announceMutation.mutate(undefined, {
                      onSuccess: () => setAnnounceOpen(false),
                    })
                  }
                  disabled={!canAnnounce || announceMutation.isPending}
                >
                  {announceMutation.isPending ? "Tasdiqlanmoqda..." : "Winnerlarni e’lon qilish"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle>Natijalar Jadvali</CardTitle>
              <CardDescription>Top-N preview va barcha arizalar ro‘yxati.</CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="top">
                <TabsList variant="line">
                  <TabsTrigger value="top">Top {results.max_winners}</TabsTrigger>
                  <TabsTrigger value="all">Barchasi</TabsTrigger>
                </TabsList>

                <TabsContent value="top" className="pt-4">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Rank</TableHead>
                        <TableHead>Student</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Score</TableHead>
                        <TableHead>Consistency</TableHead>
                        <TableHead>Submitted</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {topRows.map((row) => (
                        <TableRow key={row.application_id}>
                          <TableCell>{row.rank ?? "-"}</TableCell>
                          <TableCell className="font-medium">{row.student_name}</TableCell>
                          <TableCell>
                            <Badge variant={statusVariant(row.status)}>{statusLabel(row.status)}</Badge>
                          </TableCell>
                          <TableCell>{typeof row.total_score === "number" ? row.total_score.toFixed(2) : "-"}</TableCell>
                          <TableCell>
                            <Badge variant={consistencyVariant(row.consistency)}>{consistencyLabel(row.consistency)}</Badge>
                          </TableCell>
                          <TableCell>{formatDate(row.submitted_at)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TabsContent>

                <TabsContent value="all" className="pt-4">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Rank</TableHead>
                        <TableHead>Student</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Score</TableHead>
                        <TableHead>Consistency</TableHead>
                        <TableHead>Submitted</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {allRows.map((row) => (
                        <TableRow key={row.application_id}>
                          <TableCell>{row.rank ?? "-"}</TableCell>
                          <TableCell className="font-medium">{row.student_name}</TableCell>
                          <TableCell>
                            <Badge variant={statusVariant(row.status)}>{statusLabel(row.status)}</Badge>
                          </TableCell>
                          <TableCell>{typeof row.total_score === "number" ? row.total_score.toFixed(2) : "-"}</TableCell>
                          <TableCell>
                            <Badge variant={consistencyVariant(row.consistency)}>{consistencyLabel(row.consistency)}</Badge>
                          </TableCell>
                          <TableCell>{formatDate(row.submitted_at)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
