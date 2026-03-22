"use client"

import { ChevronDown, Sparkles } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { ApplicationValueDetail } from "@/types"

type ParsedAIAnalysis = {
  analysis: string
  strengths: string[]
  weaknesses: string[]
  recommendation: string | null
  scoreReasoning: string | null
}

type AIAnalysisAccordionProps = {
  values: ApplicationValueDetail[]
  aiSummary?: string | null
  className?: string
}

function toStringArray(raw: unknown): string[] {
  if (!Array.isArray(raw)) {
    return []
  }
  return raw.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
}

function parseAIAnalysis(raw: string | null | undefined): ParsedAIAnalysis {
  if (!raw) {
    return {
      analysis: "AI tahlili topilmadi.",
      strengths: [],
      weaknesses: [],
      recommendation: null,
      scoreReasoning: null,
    }
  }

  const trimmed = raw.trim()
  if (!trimmed) {
    return {
      analysis: "AI tahlili topilmadi.",
      strengths: [],
      weaknesses: [],
      recommendation: null,
      scoreReasoning: null,
    }
  }

  if (trimmed.startsWith("{")) {
    try {
      const parsed = JSON.parse(trimmed) as Record<string, unknown>
      return {
        analysis: typeof parsed.analysis === "string" ? parsed.analysis : trimmed,
        strengths: toStringArray(parsed.strengths),
        weaknesses: toStringArray(parsed.weaknesses),
        recommendation: typeof parsed.recommendation === "string" ? parsed.recommendation : null,
        scoreReasoning: typeof parsed.score_reasoning === "string" ? parsed.score_reasoning : null,
      }
    } catch {
      return {
        analysis: trimmed,
        strengths: [],
        weaknesses: [],
        recommendation: null,
        scoreReasoning: null,
      }
    }
  }

  return {
    analysis: trimmed,
    strengths: [],
    weaknesses: [],
    recommendation: null,
    scoreReasoning: null,
  }
}

function recommendationLabel(value: string | null): string | null {
  if (!value) {
    return null
  }
  if (value === "outstanding") {
    return "Outstanding"
  }
  if (value === "accept") {
    return "Accept"
  }
  if (value === "improve") {
    return "Improve"
  }
  return value
}

export default function AIAnalysisAccordion({ values, aiSummary, className }: AIAnalysisAccordionProps) {
  const analyzedValues = values.filter((value) => value.column?.ai_analyze)

  return (
    <Card className={cn("border-slate-200", className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="h-4 w-4 text-slate-700" />
          AI Xulosalar
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {aiSummary && <div className="rounded-md bg-slate-50 p-3 text-sm text-slate-700">{aiSummary}</div>}

        {analyzedValues.length === 0 ? (
          <p className="text-sm text-slate-500">Bu ariza uchun `ai_analyze=true` ustunlarda tahlil mavjud emas.</p>
        ) : (
          analyzedValues.map((value, index) => {
            const parsed = parseAIAnalysis(value.ai_analysis)
            const reco = recommendationLabel(parsed.recommendation)
            return (
              <details
                key={value.id ?? `${value.column_id}-${index}`}
                className="group rounded-lg border border-slate-200 bg-white open:border-slate-300"
              >
                <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-slate-900">
                      {value.column?.name ?? `Ustun ${index + 1}`}
                    </p>
                    <div className="mt-1 flex flex-wrap gap-2">
                      <Badge variant="outline">AI analyze</Badge>
                      {typeof value.ai_score === "number" && (
                        <Badge variant="secondary">AI ball: {value.ai_score}</Badge>
                      )}
                      {reco && <Badge>{reco}</Badge>}
                    </div>
                  </div>
                  <ChevronDown className="h-4 w-4 text-slate-500 transition-transform group-open:rotate-180" />
                </summary>

                <div className="space-y-3 border-t border-slate-100 px-4 py-3">
                  <div>
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Tahlil</p>
                    <p className="text-sm text-slate-700">{parsed.analysis}</p>
                  </div>

                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="rounded-md bg-emerald-50 p-3">
                      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-emerald-700">
                        Strengths
                      </p>
                      {parsed.strengths.length === 0 ? (
                        <p className="text-sm text-emerald-800/80">Kuchli tomonlar ajratilmagan.</p>
                      ) : (
                        <ul className="list-disc space-y-1 pl-4 text-sm text-emerald-900">
                          {parsed.strengths.map((item, i) => (
                            <li key={`${value.id}-s-${i}`}>{item}</li>
                          ))}
                        </ul>
                      )}
                    </div>

                    <div className="rounded-md bg-amber-50 p-3">
                      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-amber-700">
                        Weaknesses
                      </p>
                      {parsed.weaknesses.length === 0 ? (
                        <p className="text-sm text-amber-800/80">Kamchiliklar ajratilmagan.</p>
                      ) : (
                        <ul className="list-disc space-y-1 pl-4 text-sm text-amber-900">
                          {parsed.weaknesses.map((item, i) => (
                            <li key={`${value.id}-w-${i}`}>{item}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>

                  {parsed.scoreReasoning && (
                    <div className="rounded-md bg-slate-50 p-3">
                      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Score Reasoning
                      </p>
                      <p className="text-sm text-slate-700">{parsed.scoreReasoning}</p>
                    </div>
                  )}
                </div>
              </details>
            )
          })
        )}
      </CardContent>
    </Card>
  )
}
