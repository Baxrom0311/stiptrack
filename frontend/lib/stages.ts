import api from "@/lib/api"
import type { StageTask, StageTaskInput, WorkflowStage, WorkflowStageInput } from "@/types"

export async function listStages(scholarshipId: string): Promise<WorkflowStage[]> {
  const { data } = await api.get<WorkflowStage[]>(`/scholarships/${scholarshipId}/stages`)
  return data
}

export async function createStage(scholarshipId: string, payload: WorkflowStageInput): Promise<WorkflowStage> {
  const { data } = await api.post<WorkflowStage>(`/scholarships/${scholarshipId}/stages`, payload)
  return data
}

export async function deleteStage(scholarshipId: string, stageId: string): Promise<void> {
  await api.delete(`/scholarships/${scholarshipId}/stages/${stageId}`)
}

export async function listStageTasks(scholarshipId: string, stageId: string): Promise<StageTask[]> {
  const { data } = await api.get<StageTask[]>(`/scholarships/${scholarshipId}/stages/${stageId}/tasks`)
  return data
}

export async function createStageTask(
  scholarshipId: string,
  stageId: string,
  payload: StageTaskInput,
): Promise<StageTask> {
  const { data } = await api.post<StageTask>(`/scholarships/${scholarshipId}/stages/${stageId}/tasks`, payload)
  return data
}

export async function deleteStageTask(scholarshipId: string, stageId: string, taskId: string): Promise<void> {
  await api.delete(`/scholarships/${scholarshipId}/stages/${stageId}/tasks/${taskId}`)
}
