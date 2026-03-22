"use client"

import Link from "next/link"

import { Badge } from "@/components/ui/badge"
import type { ApplicationValueDetail } from "@/types"

type PlagiarismSummaryProps = {
  value: ApplicationValueDetail
  canOpenMatches?: boolean
}

function plagiarismBadgeVariant(score: number | null | undefined): "default" | "secondary" | "outline" | "destructive" {
  if (typeof score !== "number") {
    return "outline"
  }
  if (score >= 85) {
    return "destructive"
  }
  if (score >= 70) {
    return "secondary"
  }
  return "outline"
}

function plagiarismLabel(score: number | null | undefined): string {
  if (typeof score !== "number") {
    return "Tekshirilmagan"
  }
  if (score >= 85) {
    return "Yuqori o‘xshashlik"
  }
  if (score >= 70) {
    return "Shubhali o‘xshashlik"
  }
  return "Past o‘xshashlik"
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

export default function PlagiarismSummary({ value, canOpenMatches = false }: PlagiarismSummaryProps) {
  const matches = value.plagiarism_matches ?? []

  return (
    <div className="mt-3 rounded-xl border border-dashed border-rose-200 bg-rose-50/60 p-3 text-sm text-slate-700">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-xs uppercase tracking-wide text-slate-500">Plagiarism check</p>
        <Badge variant={plagiarismBadgeVariant(value.plagiarism_score)}>{plagiarismLabel(value.plagiarism_score)}</Badge>
        {typeof value.plagiarism_score === "number" && (
          <Badge variant="outline">Max overlap: {value.plagiarism_score.toFixed(2)}%</Badge>
        )}
      </div>

      <p className="mt-2 text-xs text-slate-500">Oxirgi tekshiruv: {formatDate(value.plagiarism_checked_at)}</p>

      {matches.length === 0 ? (
        <p className="mt-2 text-sm text-slate-700">
          {typeof value.plagiarism_score === "number"
            ? "Thresholddan yuqori match topilmadi."
            : "Bu field uchun plagiarism check hali ishlamagan yoki matn yo‘q."}
        </p>
      ) : (
        <div className="mt-3 grid gap-2">
          {matches.map((match, index) => (
            <div key={`${value.id}-match-${index}`} className="rounded-lg border border-rose-200 bg-white/80 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{match.similarity_percent.toFixed(2)}%</Badge>
                <Badge variant="secondary">Status: {match.application_status}</Badge>
                {canOpenMatches && match.application_id && (
                  <Link
                    href={`/admin/applications/${match.application_id}`}
                    className="text-xs font-medium text-rose-700 underline"
                  >
                    Match ariza
                  </Link>
                )}
              </div>
              <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{match.matched_text_excerpt}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
