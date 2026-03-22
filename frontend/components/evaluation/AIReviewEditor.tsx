"use client"

import { useMutation, useQuery } from "@tanstack/react-query"
import { Loader2, Save, WandSparkles } from "lucide-react"
import { useEffect, useMemo, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import {
  createEvaluation,
  generateAIReview,
  getEvaluation,
  updateEvaluation,
} from "@/lib/evaluations"
import { notifyError, notifySuccess } from "@/lib/notifications"
import type { AIReviewResponse, Evaluation } from "@/types"

type AIReviewEditorProps = {
  applicationId: string
  className?: string
}

export default function AIReviewEditor({ applicationId, className }: AIReviewEditorProps) {
  const [juryNotes, setJuryNotes] = useState("")
  const [reviewText, setReviewText] = useState("")
  const [aiGenerated, setAIGenerated] = useState(false)
  const [lastAIReview, setLastAIReview] = useState<AIReviewResponse | null>(null)
  const [isDirty, setIsDirty] = useState(false)

  const evaluationQuery = useQuery({
    queryKey: ["evaluation-editor", applicationId],
    queryFn: () => getEvaluation(applicationId),
    retry: 0,
  })

  useEffect(() => {
    if (!evaluationQuery.data || isDirty) {
      return
    }
    setReviewText(evaluationQuery.data.final_comment || "")
    setAIGenerated(evaluationQuery.data.ai_generated)
  }, [evaluationQuery.data, isDirty])

  const ensureEvaluation = async (): Promise<Evaluation> => {
    const current = evaluationQuery.data ?? (await getEvaluation(applicationId))
    if (current.id) {
      return current
    }
    try {
      return await createEvaluation(applicationId)
    } catch {
      return getEvaluation(applicationId)
    }
  }

  const generateMutation = useMutation({
    mutationFn: async () => {
      await ensureEvaluation()
      return generateAIReview(applicationId, juryNotes)
    },
    onSuccess: async (result) => {
      setLastAIReview(result)
      setReviewText(result.review_text)
      setAIGenerated(true)
      setIsDirty(true)
      notifySuccess("AI tahlil muvaffaqiyatli yaratildi.")
      await evaluationQuery.refetch()
    },
    onError: (error) => {
      notifyError(error)
    },
  })

  const saveMutation = useMutation({
    mutationFn: async () => {
      await ensureEvaluation()
      return updateEvaluation(applicationId, {
        final_comment: reviewText,
        ai_generated: aiGenerated,
      })
    },
    onSuccess: (evaluation) => {
      setReviewText(evaluation.final_comment || "")
      setAIGenerated(evaluation.ai_generated)
      setIsDirty(false)
      notifySuccess("Tahlil saqlandi.")
      void evaluationQuery.refetch()
    },
    onError: (error) => {
      notifyError(error)
    },
  })

  const isBusy = generateMutation.isPending || saveMutation.isPending
  const canSave = useMemo(() => reviewText.trim().length > 0 && !isBusy, [isBusy, reviewText])

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          AIReviewEditor
          {aiGenerated && <Badge>AI yordamida yaratildi</Badge>}
        </CardTitle>
        <CardDescription>
          Hakam izohlarini kiriting, AI bilan yakuniy tahlil yarating va tahrirlab saqlang.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <p className="text-sm font-medium text-slate-700">Jury notes (ixtiyoriy)</p>
          <Textarea
            placeholder="Masalan: talabada ilmiy yo'nalish kuchli, lekin hujjatlar orasida tafovut bor..."
            value={juryNotes}
            onChange={(event) => setJuryNotes(event.target.value)}
            className="min-h-20"
          />
        </div>

        <Button type="button" onClick={() => generateMutation.mutate()} disabled={isBusy}>
          {generateMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              AI tahlil yozmoqda...
            </>
          ) : (
            <>
              <WandSparkles className="mr-2 h-4 w-4" />
              AI bilan tahlil yozish
            </>
          )}
        </Button>

        {lastAIReview && (
          <div className="grid gap-2 rounded-md bg-slate-50 p-3 text-xs text-slate-600 sm:grid-cols-3">
            <p>Ball: {lastAIReview.total_score}</p>
            <p>Maks: {lastAIReview.max_total_score}</p>
            <p>Foiz: {lastAIReview.score_percent}%</p>
          </div>
        )}

        <div className="space-y-2">
          <p className="text-sm font-medium text-slate-700">Yakuniy tahlil</p>
          <Textarea
            value={reviewText}
            onChange={(event) => {
              setReviewText(event.target.value)
              setIsDirty(true)
            }}
            placeholder="AI natijasi yoki qo'lda yozilgan yakuniy tahlil shu yerda bo'ladi."
            className="min-h-40"
          />
        </div>

        <Button type="button" variant="outline" onClick={() => saveMutation.mutate()} disabled={!canSave}>
          {saveMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Saqlanmoqda...
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              Saqlash
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  )
}
