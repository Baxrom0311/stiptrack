import api from "@/lib/api"
import { validateSelectedFile } from "@/lib/file-validation"
import type { AIJob, NizomParseResponse, SuggestColumnsResult } from "@/types"

export type GenerateColumnsPayload = {
  purpose: string
  requirements: string[]
  evaluation_criteria: Array<string | object>
  additional_docs: string[]
  total_max_score: number
  scoring_type: string
  eligible_students?: string | null
  selection_stages?: string | null
}

export async function uploadNizomPdf(scholarshipId: string, file: File): Promise<string> {
  const validationError = validateSelectedFile(file, "nizom")
  if (validationError) {
    throw new Error(validationError)
  }

  const formData = new FormData()
  formData.append("file", file)

  const { data } = await api.post<{ nizom_file_url: string }>(
    `/scholarships/${scholarshipId}/upload-nizom`,
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    },
  )

  return data.nizom_file_url
}

export async function parseNizom(scholarshipId: string): Promise<NizomParseResponse> {
  const { data } = await api.post<NizomParseResponse>(`/ai/scholarships/${scholarshipId}/parse-nizom`)
  return data
}

export async function generateColumns(
  scholarshipId: string,
  payload: GenerateColumnsPayload,
): Promise<{ detail: string; job_id: string }> {
  const { data } = await api.post<{ detail: string; job_id: string }>(
    `/ai/scholarships/${scholarshipId}/generate-columns`,
    payload,
  )
  return data
}

export async function getAIJobStatus(jobId: string): Promise<AIJob> {
  const { data } = await api.get<AIJob>(`/ai/jobs/${jobId}`)
  return data
}

export function parseSuggestColumnsResult(raw: unknown): SuggestColumnsResult | null {
  if (typeof raw !== "object" || raw === null) {
    return null
  }

  const candidate = raw as Record<string, unknown>
  const rawColumns = candidate.columns
  if (!Array.isArray(rawColumns)) {
    return null
  }

  const columns: SuggestColumnsResult["columns"] = rawColumns.flatMap((column) => {
    if (typeof column !== "object" || column === null) {
      return []
    }

    const item = column as Record<string, unknown>
    if (
      typeof item.name !== "string" ||
      typeof item.description !== "string" ||
      typeof item.field_type !== "string" ||
      typeof item.is_required !== "boolean" ||
      typeof item.ai_analyze !== "boolean" ||
      typeof item.max_score !== "number" ||
      typeof item.order_index !== "number"
    ) {
      return []
    }

    return [
      {
        name: item.name,
        criterion_ref: typeof item.criterion_ref === "string" ? item.criterion_ref : "umumiy",
        description: item.description,
        field_type: item.field_type as SuggestColumnsResult["columns"][number]["field_type"],
        select_options: Array.isArray(item.select_options)
          ? item.select_options.filter((option): option is string => typeof option === "string")
          : null,
        is_required: item.is_required,
        ai_analyze: item.ai_analyze,
        max_score: item.max_score,
        input_min: typeof item.input_min === "number" ? item.input_min : null,
        input_max: typeof item.input_max === "number" ? item.input_max : null,
        order_index: item.order_index,
        validation_hint: typeof item.validation_hint === "string" ? item.validation_hint : null,
      },
    ]
  })

  return {
    columns,
    total_max_score: typeof candidate.total_max_score === "number" ? candidate.total_max_score : 0,
    ai_columns_count: typeof candidate.ai_columns_count === "number" ? candidate.ai_columns_count : 0,
    reasoning: typeof candidate.reasoning === "string" ? candidate.reasoning : "",
  }
}
