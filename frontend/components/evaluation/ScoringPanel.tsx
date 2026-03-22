"use client"

import { useMutation, useQuery } from "@tanstack/react-query"
import { CheckCircle2, Loader2, Save, Send } from "lucide-react"
import { useEffect, useMemo, useState } from "react"

import AIAnalysisAccordion from "@/components/evaluation/AIAnalysisAccordion"
import AIReviewEditor from "@/components/evaluation/AIReviewEditor"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
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
import { FormCardSkeleton } from "@/components/ui/page-skeletons"
import { Textarea } from "@/components/ui/textarea"
import {
  createEvaluation,
  getEvaluation,
  submitEvaluation,
  updateEvaluation,
} from "@/lib/evaluations"
import { notifyError, notifySuccess } from "@/lib/notifications"
import type { ApplicationDetailResponse, Column, Evaluation } from "@/types"

type ScoringPanelProps = {
  application: ApplicationDetailResponse
  className?: string
}

const SCORE_STEP = 0.5

function normalizeScore(value: number, maxScore: number): number {
  if (!Number.isFinite(value)) {
    return 0
  }
  if (value < 0) {
    return 0
  }
  if (value > maxScore) {
    return maxScore
  }
  return Math.round(value * 100) / 100
}

function uniqueColumnsFromApplication(application: ApplicationDetailResponse): Column[] {
  const scholarshipColumns = application.scholarship?.columns ?? []
  if (scholarshipColumns.length > 0) {
    return scholarshipColumns
  }

  const fromValues: Column[] = []
  const seen = new Set<string>()
  for (const value of application.values) {
    if (!value.column || seen.has(value.column.id)) {
      continue
    }
    seen.add(value.column.id)
    fromValues.push(value.column)
  }
  return fromValues
}

export default function ScoringPanel({ application, className }: ScoringPanelProps) {
  const [scores, setScores] = useState<Record<string, number>>({})
  const [isDirty, setIsDirty] = useState(false)
  const [submitOpen, setSubmitOpen] = useState(false)
  const [columnNotes, setColumnNotes] = useState<Record<string, string>>({})

  const allColumns = useMemo(() => uniqueColumnsFromApplication(application), [application])
  const scorableColumns = useMemo(() => allColumns.filter((column) => column.max_score > 0), [allColumns])

  const maxTotalScore = useMemo(
    () => scorableColumns.reduce((acc, column) => acc + column.max_score, 0),
    [scorableColumns],
  )
  const currentTotalScore = useMemo(
    () => scorableColumns.reduce((acc, column) => acc + (scores[column.id] ?? 0), 0),
    [scorableColumns, scores],
  )
  const currentPercent = useMemo(
    () => (maxTotalScore > 0 ? Math.round((currentTotalScore / maxTotalScore) * 10000) / 100 : 0),
    [currentTotalScore, maxTotalScore],
  )

  const aiScoreByColumn = useMemo(() => {
    const map: Record<string, number> = {}
    for (const value of application.values) {
      if (value.column_id && typeof value.ai_score === "number") {
        map[value.column_id] = value.ai_score
      }
    }
    return map
  }, [application.values])

  const evaluationQuery = useQuery({
    queryKey: ["jury-scoring-evaluation", application.id],
    queryFn: () => getEvaluation(application.id),
    retry: 0,
  })

  const canEdit = !evaluationQuery.data?.is_submitted

  useEffect(() => {
    if (!evaluationQuery.data || isDirty) {
      return
    }
    const nextScores: Record<string, number> = {}
    for (const column of scorableColumns) {
      const existing = evaluationQuery.data.scores?.[column.id]
      nextScores[column.id] = normalizeScore(typeof existing === "number" ? existing : 0, column.max_score)
    }
    setScores(nextScores)
  }, [evaluationQuery.data, isDirty, scorableColumns])

  useEffect(() => {
    if (typeof window === "undefined") {
      return
    }
    const raw = localStorage.getItem(`jury:column-notes:${application.id}`)
    if (!raw) {
      return
    }
    try {
      const parsed = JSON.parse(raw) as Record<string, string>
      setColumnNotes(parsed)
    } catch {
      setColumnNotes({})
    }
  }, [application.id])

  useEffect(() => {
    if (typeof window === "undefined") {
      return
    }
    localStorage.setItem(`jury:column-notes:${application.id}`, JSON.stringify(columnNotes))
  }, [application.id, columnNotes])

  const ensureEvaluation = async (): Promise<Evaluation> => {
    const current = evaluationQuery.data ?? (await getEvaluation(application.id))
    if (current.id) {
      return current
    }
    try {
      return await createEvaluation(application.id)
    } catch {
      return getEvaluation(application.id)
    }
  }

  const saveMutation = useMutation({
    mutationFn: async (nextScores: Record<string, number>) => {
      await ensureEvaluation()
      return updateEvaluation(application.id, { scores: nextScores })
    },
    onSuccess: async () => {
      setIsDirty(false)
      notifySuccess("Qoralama saqlandi.")
      await evaluationQuery.refetch()
    },
    onError: (error) => {
      notifyError(error)
    },
  })

  useEffect(() => {
    if (!canEdit || !isDirty || saveMutation.isPending) {
      return
    }

    const timer = setTimeout(() => {
      saveMutation.mutate(scores)
    }, 3000)

    return () => clearTimeout(timer)
  }, [canEdit, isDirty, saveMutation, scores])

  const submitMutation = useMutation({
    mutationFn: async () => {
      await ensureEvaluation()
      if (isDirty) {
        await updateEvaluation(application.id, { scores })
      }
      return submitEvaluation(application.id)
    },
    onSuccess: async () => {
      setIsDirty(false)
      setSubmitOpen(false)
      notifySuccess("Baholash topshirildi.")
      await evaluationQuery.refetch()
    },
    onError: (error) => {
      notifyError(error)
      setSubmitOpen(false)
    },
  })

  const handleScoreChange = (columnId: string, rawValue: string | number, maxScore: number) => {
    const parsed = typeof rawValue === "number" ? rawValue : Number(rawValue)
    const normalized = normalizeScore(parsed, maxScore)
    setScores((prev) => ({ ...prev, [columnId]: normalized }))
    setIsDirty(true)
  }

  if (evaluationQuery.isLoading) {
    return <FormCardSkeleton className={className} fields={6} actions={2} />
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-lg">ScoringPanel</CardTitle>
        <CardDescription>
          Ustunlar bo‘yicha ball qo‘ying. Qoralama 3 soniyada auto-save qilinadi.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <AIAnalysisAccordion values={application.values} aiSummary={application.ai_summary} />

        <div className="grid gap-5 xl:grid-cols-[1fr_260px]">
          <div className="space-y-4">
            {scorableColumns.map((column) => {
              const score = scores[column.id] ?? 0
              return (
                <div key={column.id} className="rounded-lg border border-slate-200 p-4">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold text-slate-900">{column.name}</p>
                    <Badge variant="outline">max: {column.max_score}</Badge>
                    {typeof aiScoreByColumn[column.id] === "number" && (
                      <Badge variant="secondary">AI score: {aiScoreByColumn[column.id]}</Badge>
                    )}
                  </div>
                  {column.description && <p className="mb-3 text-xs text-slate-600">{column.description}</p>}

                  <div className="grid gap-3 sm:grid-cols-[1fr_120px] sm:items-center">
                    <input
                      type="range"
                      min={0}
                      max={column.max_score}
                      step={SCORE_STEP}
                      value={score}
                      onChange={(event) => handleScoreChange(column.id, event.target.value, column.max_score)}
                      disabled={!canEdit || saveMutation.isPending || submitMutation.isPending}
                    />
                    <Input
                      type="number"
                      step={SCORE_STEP}
                      min={0}
                      max={column.max_score}
                      value={String(score)}
                      onChange={(event) => handleScoreChange(column.id, event.target.value, column.max_score)}
                      disabled={!canEdit || saveMutation.isPending || submitMutation.isPending}
                    />
                  </div>

                  <div className="mt-3">
                    <p className="mb-1 text-xs font-medium text-slate-600">Ustun izohi (ixtiyoriy)</p>
                    <Textarea
                      className="min-h-16"
                      placeholder="Bu ustun bo‘yicha qisqa izoh..."
                      value={columnNotes[column.id] ?? ""}
                      onChange={(event) =>
                        setColumnNotes((prev) => ({
                          ...prev,
                          [column.id]: event.target.value,
                        }))
                      }
                      disabled={!canEdit}
                    />
                  </div>
                </div>
              )
            })}

            <AIReviewEditor applicationId={application.id} />
          </div>

          <div className="space-y-3">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Umumiy ball</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="text-sm text-slate-700">
                  <p>
                    {currentTotalScore.toFixed(2)} / {maxTotalScore.toFixed(2)}
                  </p>
                  <p className="text-xs text-slate-500">{currentPercent.toFixed(2)}%</p>
                </div>

                {evaluationQuery.data?.is_submitted ? (
                  <Badge>
                    <CheckCircle2 className="mr-1 h-3 w-3" />
                    Topshirilgan
                  </Badge>
                ) : (
                  <Badge variant="outline">Draft</Badge>
                )}
              </CardContent>
            </Card>

            <Button
              type="button"
              variant="outline"
              disabled={!canEdit || saveMutation.isPending || !isDirty}
              onClick={() => saveMutation.mutate(scores)}
              className="w-full"
            >
              {saveMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saqlanmoqda...
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  Qoralama saqlash
                </>
              )}
            </Button>

            <Button
              type="button"
              disabled={!canEdit || submitMutation.isPending}
              onClick={() => setSubmitOpen(true)}
              className="w-full"
            >
              {submitMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Topshirilmoqda...
                </>
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" />
                  Topshirish
                </>
              )}
            </Button>
          </div>
        </div>
      </CardContent>

      <Dialog open={submitOpen} onOpenChange={setSubmitOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Baholashni topshirish</DialogTitle>
            <DialogDescription>
              Topshirgandan keyin balllarni o‘zgartirib bo‘lmaydi. Davom etasizmi?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSubmitOpen(false)}>
              Bekor qilish
            </Button>
            <Button onClick={() => submitMutation.mutate()} disabled={submitMutation.isPending}>
              Tasdiqlash
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
