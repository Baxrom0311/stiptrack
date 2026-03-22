"use client"

import { FileUp, Loader2, WandSparkles } from "lucide-react"
import { useCallback, useMemo, useRef, useState } from "react"

import AIJobStatus from "@/components/ai/AIJobStatus"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  generateColumns,
  parseNizom,
  parseSuggestColumnsResult,
  uploadNizomPdf,
  type GenerateColumnsPayload,
} from "@/lib/ai"
import { formatFileSizeLimit, getFileValidationRule, validateSelectedFile } from "@/lib/file-validation"
import { notifyError, notifySuccess, notifyWarning } from "@/lib/notifications"
import { cn } from "@/lib/utils"
import type { AIJob, NizomParseResponse, SuggestedColumn } from "@/types"

type NizomUploaderProps = {
  scholarshipId: string
  className?: string
  onImportColumns?: (columns: SuggestedColumn[]) => void
}

const NIZOM_VALIDATION_RULE = getFileValidationRule("nizom")

function formatSize(size: number) {
  const mb = size / (1024 * 1024)
  return `${mb.toFixed(2)} MB`
}

function buildGeneratePayload(parseResult: NizomParseResponse): GenerateColumnsPayload {
  return {
    purpose: parseResult.purpose,
    requirements: parseResult.requirements,
    evaluation_criteria:
      parseResult.evaluation_criteria_detailed.length > 0
        ? parseResult.evaluation_criteria_detailed
        : parseResult.evaluation_criteria,
    additional_docs: parseResult.additional_docs,
    total_max_score: parseResult.total_max_score,
    scoring_type: parseResult.scoring_type,
    eligible_students: parseResult.eligible_students,
    selection_stages: parseResult.selection_stages,
  }
}

export default function NizomUploader({ scholarshipId, className, onImportColumns }: NizomUploaderProps) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [jobId, setJobId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [parseData, setParseData] = useState<NizomParseResponse | null>(null)
  const [suggestedColumns, setSuggestedColumns] = useState<SuggestedColumn[]>([])
  const [selectedMap, setSelectedMap] = useState<Record<string, boolean>>({})
  const [importMessage, setImportMessage] = useState<string | null>(null)

  const selectedColumns = useMemo(
    () => suggestedColumns.filter((_, index) => selectedMap[String(index)]),
    [selectedMap, suggestedColumns],
  )

  const resetResultState = useCallback(() => {
    setJobId(null)
    setParseData(null)
    setSuggestedColumns([])
    setSelectedMap({})
    setImportMessage(null)
  }, [])

  const setFileWithValidation = useCallback((nextFile: File | null) => {
    if (!nextFile) {
      return
    }
    const message = validateSelectedFile(nextFile, "nizom")
    if (message) {
      setError(message)
      notifyWarning(message)
      return
    }
    setError(null)
    setFile(nextFile)
  }, [])

  const handleGenerate = useCallback(async () => {
    if (!scholarshipId.trim()) {
      const message = "Avval scholarship ID kiriting."
      setError(message)
      notifyWarning(message)
      return
    }
    if (!file) {
      const message = "Avval PDF nizom faylini tanlang."
      setError(message)
      notifyWarning(message)
      return
    }

    setError(null)
    setImportMessage(null)
    setIsGenerating(true)
    resetResultState()

    try {
      await uploadNizomPdf(scholarshipId, file)
      const parsed = await parseNizom(scholarshipId)
      setParseData(parsed)

      const generated = await generateColumns(scholarshipId, buildGeneratePayload(parsed))
      setJobId(generated.job_id)
    } catch (rawError) {
      const message = rawError instanceof Error ? rawError.message : "AI jarayonini ishga tushirishda xatolik bo'ldi."
      setError(message)
      notifyError(message)
    } finally {
      setIsGenerating(false)
    }
  }, [file, resetResultState, scholarshipId])

  const handleJobDone = useCallback((job: AIJob) => {
    const parsed = parseSuggestColumnsResult(job.result)
    if (!parsed || parsed.columns.length === 0) {
      const message = "AI natijasi ichida ustunlar topilmadi."
      setError(message)
      notifyError(message)
      return
    }

    const normalized = parsed.columns
      .slice()
      .sort((a, b) => a.order_index - b.order_index)
      .map((column, index) => ({ ...column, order_index: index }))

    const nextSelection: Record<string, boolean> = {}
    for (let index = 0; index < normalized.length; index += 1) {
      nextSelection[String(index)] = true
    }

    setSuggestedColumns(normalized)
    setSelectedMap(nextSelection)
    setError(null)
    notifySuccess(`${normalized.length} ta AI ustuni tayyorlandi.`)
  }, [])

  const handleJobFailed = useCallback((job: AIJob) => {
    const message = job.error_msg || "AI job xato bilan tugadi."
    setError(message)
    notifyError(message)
  }, [])

  const handleImport = useCallback(() => {
    if (selectedColumns.length === 0) {
      const message = "Kamida 1 ta ustunni tanlang."
      setImportMessage(message)
      notifyWarning(message)
      return
    }
    onImportColumns?.(selectedColumns)
    const message = `${selectedColumns.length} ta ustun importga tayyorlandi.`
    setImportMessage(message)
    notifySuccess(message)
  }, [onImportColumns, selectedColumns])

  return (
    <Card className={cn("border-slate-200", className)}>
      <CardHeader>
        <CardTitle className="text-base">NizomUploader</CardTitle>
        <CardDescription>PDF nizom yuklang, AI yordamida ustunlarni avtomatik yarating.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div
          className={cn(
            "rounded-lg border border-dashed p-5 transition-colors",
            isDragging ? "border-slate-900 bg-slate-50" : "border-slate-300 bg-white",
          )}
          onDragOver={(event) => {
            event.preventDefault()
            setIsDragging(true)
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(event) => {
            event.preventDefault()
            setIsDragging(false)
            const droppedFile = event.dataTransfer.files?.[0] ?? null
            setFileWithValidation(droppedFile)
          }}
        >
          <input
            ref={inputRef}
            type="file"
            accept={NIZOM_VALIDATION_RULE.accept}
            className="hidden"
            onChange={(event) => setFileWithValidation(event.target.files?.[0] ?? null)}
          />

          <div className="flex flex-col items-center justify-center gap-2 text-center">
            <FileUp className="h-8 w-8 text-slate-600" />
            <p className="text-sm text-slate-700">PDF ni shu yerga tashlang yoki tugma orqali tanlang.</p>
            <Button type="button" variant="outline" size="sm" onClick={() => inputRef.current?.click()}>
              Fayl tanlash
            </Button>
            <p className="text-xs text-slate-500">
              Maksimal hajm: {formatFileSizeLimit(NIZOM_VALIDATION_RULE.maxSizeBytes)}
            </p>
          </div>
        </div>

        {file && (
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
            <p className="font-medium text-slate-800">{file.name}</p>
            <p className="text-slate-600">{formatSize(file.size)}</p>
          </div>
        )}

        <Button
          type="button"
          onClick={handleGenerate}
          disabled={isGenerating || !file || !scholarshipId.trim()}
          className="w-full"
        >
          {isGenerating ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              AI tahlil qilmoqda...
            </>
          ) : (
            <>
              <WandSparkles className="mr-2 h-4 w-4" />
              AI bilan ustunlar yaratish
            </>
          )}
        </Button>

        {jobId && (
          <AIJobStatus
            jobId={jobId}
            title="AI ustun generatsiyasi"
            onDone={handleJobDone}
            onFailed={handleJobFailed}
          />
        )}

        {parseData && (
          <div className="rounded-lg border border-slate-200 p-4">
            <p className="text-sm font-semibold text-slate-900">{parseData.title || "Nizom tahlili"}</p>
            <p className="mt-1 text-sm text-slate-600">{parseData.purpose || "Maqsad aniqlanmadi."}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge variant="outline">Talablar: {parseData.requirements.length}</Badge>
              <Badge variant="outline">Mezonlar: {parseData.evaluation_criteria_detailed.length}</Badge>
              <Badge variant="outline">Jami ball: {parseData.total_max_score}</Badge>
            </div>
          </div>
        )}

        {suggestedColumns.length > 0 && (
          <div className="space-y-3 rounded-lg border border-slate-200 p-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-slate-900">Taklif qilingan ustunlar</p>
              <Badge variant="secondary">Tanlangan: {selectedColumns.length}</Badge>
            </div>

            <div className="space-y-2">
              {suggestedColumns.map((column, index) => {
                const key = String(index)
                const checked = Boolean(selectedMap[key])
                return (
                  <label
                    key={`${column.name}-${index}`}
                    className={cn(
                      "flex cursor-pointer items-start gap-3 rounded-md border p-3",
                      checked ? "border-slate-900 bg-slate-50" : "border-slate-200 bg-white",
                    )}
                  >
                    <input
                      type="checkbox"
                      className="mt-0.5 h-4 w-4 rounded border-slate-300"
                      checked={checked}
                      onChange={(event) =>
                        setSelectedMap((prev) => ({
                          ...prev,
                          [key]: event.target.checked,
                        }))
                      }
                    />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-900">{column.name}</p>
                      <p className="mt-0.5 text-xs text-slate-600">{column.description}</p>
                      <div className="mt-2 flex flex-wrap gap-2 text-xs">
                        <Badge variant="outline">type: {column.field_type}</Badge>
                        <Badge variant="outline">max: {column.max_score}</Badge>
                        {column.field_type === "number" && (column.input_min != null || column.input_max != null) && (
                          <Badge variant="outline">
                            range: {column.input_min ?? "-"} - {column.input_max ?? "-"}
                          </Badge>
                        )}
                        {column.ai_analyze && <Badge>AI analyze</Badge>}
                      </div>
                    </div>
                  </label>
                )
              })}
            </div>

            <Button type="button" onClick={handleImport} className="w-full">
              Tanlangan ustunlarni import qilish
            </Button>
          </div>
        )}

        {(error || importMessage) && (
          <div
            className={cn(
              "rounded-md p-3 text-sm",
              error ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700",
            )}
          >
            {error || importMessage}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
