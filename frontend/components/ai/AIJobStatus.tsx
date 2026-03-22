"use client"

import { useQuery } from "@tanstack/react-query"
import { AlertCircle, CheckCircle2, Loader2, RefreshCw } from "lucide-react"
import { useEffect, useMemo, useRef } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { getAIJobStatus } from "@/lib/ai"
import { cn } from "@/lib/utils"
import type { AIJob } from "@/types"

type AIJobStatusProps = {
  jobId: string | null
  title?: string
  className?: string
  onDone?: (job: AIJob) => void
  onFailed?: (job: AIJob) => void
}

const STATUS_META: Record<
  AIJob["status"],
  { label: string; percent: number; badge: "outline" | "secondary" | "default" | "destructive" }
> = {
  pending: { label: "Pending", percent: 20, badge: "outline" },
  running: { label: "Running", percent: 70, badge: "secondary" },
  done: { label: "Done", percent: 100, badge: "default" },
  failed: { label: "Failed", percent: 100, badge: "destructive" },
}

export default function AIJobStatus({
  jobId,
  title = "AI Job Holati",
  className,
  onDone,
  onFailed,
}: AIJobStatusProps) {
  const handledRef = useRef<string | null>(null)

  const query = useQuery({
    queryKey: ["ai-job-status", jobId],
    queryFn: () => getAIJobStatus(jobId as string),
    enabled: Boolean(jobId),
    refetchInterval: (queryContext) => {
      const job = queryContext.state.data
      if (!job) {
        return 2000
      }
      return job.status === "done" || job.status === "failed" ? false : 2000
    },
  })

  useEffect(() => {
    handledRef.current = null
  }, [jobId])

  useEffect(() => {
    if (!jobId || !query.data) {
      return
    }

    const marker = `${jobId}:${query.data.status}`
    if (handledRef.current === marker) {
      return
    }

    if (query.data.status === "done") {
      handledRef.current = marker
      onDone?.(query.data)
    }

    if (query.data.status === "failed") {
      handledRef.current = marker
      onFailed?.(query.data)
    }
  }, [jobId, onDone, onFailed, query.data])

  const status = query.data?.status ?? "pending"
  const meta = STATUS_META[status]

  const statusText = useMemo(() => {
    if (query.isError) {
      return "Job holatini olishda xatolik."
    }
    if (query.data?.status === "failed") {
      return query.data.error_msg || "AI job xato bilan tugadi."
    }
    if (query.data?.status === "done") {
      return "AI jarayoni muvaffaqiyatli yakunlandi."
    }
    if (query.data?.status === "running") {
      return "AI tahlil qilmoqda..."
    }
    return "Job navbatda kutmoqda..."
  }, [query.data, query.isError])

  if (!jobId) {
    return null
  }

  return (
    <Card className={cn("border-slate-200", className)}>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle className="text-sm font-semibold">{title}</CardTitle>
        <Badge variant={meta.badge}>{meta.label}</Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="h-2 w-full rounded-full bg-slate-100">
          <div
            className={cn(
              "h-2 rounded-full transition-all duration-300",
              query.data?.status === "failed" ? "bg-red-500" : "bg-slate-800",
            )}
            style={{ width: `${meta.percent}%` }}
          />
        </div>

        <div className="flex items-center gap-2 text-sm text-slate-700">
          {query.data?.status === "done" ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          ) : query.data?.status === "failed" || query.isError ? (
            <AlertCircle className="h-4 w-4 text-red-600" />
          ) : (
            <Loader2 className="h-4 w-4 animate-spin text-slate-700" />
          )}
          <p>{statusText}</p>
        </div>

        {(query.isError || query.data?.status === "failed") && (
          <Button size="sm" variant="outline" onClick={() => query.refetch()}>
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            Retry
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
