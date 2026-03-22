import api from "@/lib/api"
import { validateSelectedFile } from "@/lib/file-validation"
import type { Achievement } from "@/types"

type AchievementKind = "paper" | "award" | "project" | "cert" | "olympiad" | "other"

type AchievementCreatePayload = {
  title: string
  type?: AchievementKind | null
  date?: string | null
  description?: string | null
}

type AchievementUpdatePayload = {
  title?: string
  type?: AchievementKind | null
  date?: string | null
  description?: string | null
}

export async function listAchievements(type: AchievementKind | "all" = "all"): Promise<Achievement[]> {
  const params = type === "all" ? undefined : { type }
  const { data } = await api.get<Achievement[]>("/achievements", { params })
  return data
}

export async function createAchievement(payload: AchievementCreatePayload): Promise<Achievement> {
  const { data } = await api.post<Achievement>("/achievements", payload)
  return data
}

export async function updateAchievement(
  achievementId: string,
  payload: AchievementUpdatePayload,
): Promise<Achievement> {
  const { data } = await api.patch<Achievement>(`/achievements/${achievementId}`, payload)
  return data
}

export async function deleteAchievement(achievementId: string): Promise<void> {
  await api.delete(`/achievements/${achievementId}`)
}

export async function uploadAchievementFile(achievementId: string, file: File): Promise<string> {
  const validationError = validateSelectedFile(file, "achievement")
  if (validationError) {
    throw new Error(validationError)
  }

  const formData = new FormData()
  formData.append("file", file)
  const { data } = await api.post<{ file_url: string }>(`/achievements/${achievementId}/upload`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })
  return data.file_url
}

export type { AchievementKind, AchievementCreatePayload, AchievementUpdatePayload }
