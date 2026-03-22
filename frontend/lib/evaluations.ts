import api from "@/lib/api"
import type { AIReviewResponse, Evaluation } from "@/types"

type EvaluationUpdatePayload = {
  scores?: Record<string, number>
  final_comment?: string | null
  ai_generated?: boolean
}

export async function getEvaluation(applicationId: string): Promise<Evaluation> {
  const { data } = await api.get<Evaluation>(`/evaluations/${applicationId}`)
  return data
}

export async function listVisibleEvaluations(applicationId: string): Promise<Evaluation[]> {
  const { data } = await api.get<Evaluation[]>(`/evaluations/applications/${applicationId}/visible`)
  return data
}

export async function createEvaluation(applicationId: string): Promise<Evaluation> {
  const { data } = await api.post<Evaluation>(`/evaluations/${applicationId}`)
  return data
}

export async function updateEvaluation(
  applicationId: string,
  payload: EvaluationUpdatePayload,
): Promise<Evaluation> {
  const { data } = await api.patch<Evaluation>(`/evaluations/${applicationId}`, payload)
  return data
}

export async function submitEvaluation(applicationId: string): Promise<Evaluation> {
  const { data } = await api.post<Evaluation>(`/evaluations/${applicationId}/submit`)
  return data
}

export async function generateAIReview(
  applicationId: string,
  juryNotes?: string,
): Promise<AIReviewResponse> {
  const { data } = await api.post<AIReviewResponse>(`/ai/evaluations/${applicationId}/ai-review`, {
    jury_notes: juryNotes || null,
  })
  return data
}
