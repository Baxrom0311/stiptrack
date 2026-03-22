import type { AxiosProgressEvent } from "axios"

import api from "@/lib/api"
import type {
  ApplicationDetailResponse,
  ApplicationListItem,
  ApplicationStatus,
  ApplicationStatusLogEntry,
} from "@/types"

export type ApplicationDraftValues = Record<string, string | null>

export type ApplicationDraftPayload = {
  supervisor_id?: string | null
  values?: ApplicationDraftValues
}

type ListScholarshipApplicationsParams = {
  status?: ApplicationStatus
  skip?: number
  limit?: number
}

type FileUploadResponse = {
  file_url: string
}

type ApplicationCreateResponse = {
  application_id: string
  status: ApplicationStatus
}

export async function createOrGetApplication(scholarshipId: string): Promise<ApplicationCreateResponse> {
  const { data } = await api.post<ApplicationCreateResponse>(`/scholarships/${scholarshipId}/apply`)
  return data
}

export async function getScholarshipApplicationDraft(scholarshipId: string): Promise<ApplicationDetailResponse> {
  const { data } = await api.get<ApplicationDetailResponse>(`/scholarships/${scholarshipId}/apply`)
  return data
}

export async function getApplication(applicationId: string): Promise<ApplicationDetailResponse> {
  const { data } = await api.get<ApplicationDetailResponse>(`/applications/${applicationId}`)
  return data
}

export async function listApplicationStatusLogs(applicationId: string): Promise<ApplicationStatusLogEntry[]> {
  const { data } = await api.get<ApplicationStatusLogEntry[]>(`/applications/${applicationId}/history`)
  return data
}

export async function updateApplicationDraft(
  applicationId: string,
  payload: ApplicationDraftPayload,
): Promise<ApplicationDetailResponse> {
  const { data } = await api.patch<ApplicationDetailResponse>(`/applications/${applicationId}`, payload)
  return data
}

export async function uploadApplicationValueFile(
  applicationId: string,
  columnId: string,
  file: File,
  onProgress?: (progress: number) => void,
): Promise<string> {
  const formData = new FormData()
  formData.append("file", file)

  const { data } = await api.post<FileUploadResponse>(`/applications/${applicationId}/values/${columnId}/upload`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    onUploadProgress: (event: AxiosProgressEvent) => {
      if (!onProgress || !event.total) {
        return
      }
      onProgress(Math.min(100, Math.round((event.loaded / event.total) * 100)))
    },
  })

  return data.file_url
}

export async function submitApplication(applicationId: string): Promise<ApplicationDetailResponse> {
  const { data } = await api.post<ApplicationDetailResponse>(`/applications/${applicationId}/submit`)
  return data
}

export async function listMyApplications(): Promise<ApplicationListItem[]> {
  const { data } = await api.get<ApplicationListItem[]>("/applications/my")
  return data
}

export async function listScholarshipApplications(
  scholarshipId: string,
  params: ListScholarshipApplicationsParams = {},
): Promise<ApplicationListItem[]> {
  const { data } = await api.get<ApplicationListItem[]>(`/scholarships/${scholarshipId}/applications`, {
    params,
  })
  return data
}
