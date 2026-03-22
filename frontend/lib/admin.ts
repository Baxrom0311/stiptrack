import api from "@/lib/api"
import type { AdminStats, AnnounceWinnersResponse, ApplicationConsistency, ScholarshipResults } from "@/types"

export async function getAdminStats(): Promise<AdminStats> {
  const { data } = await api.get<AdminStats>("/admin/stats")
  return data
}

export async function getScholarshipResults(scholarshipId: string): Promise<ScholarshipResults> {
  const { data } = await api.get<ScholarshipResults>(`/admin/scholarships/${scholarshipId}/results`)
  return data
}

export async function getApplicationConsistency(applicationId: string): Promise<ApplicationConsistency> {
  const { data } = await api.get<ApplicationConsistency>(`/admin/applications/${applicationId}/consistency`)
  return data
}

export async function announceWinners(scholarshipId: string): Promise<AnnounceWinnersResponse> {
  const { data } = await api.post<AnnounceWinnersResponse>(`/scholarships/${scholarshipId}/announce-winners`)
  return data
}

function getFilenameFromContentDisposition(header?: string): string | null {
  if (!header) {
    return null
  }
  const match = header.match(/filename="?([^";]+)"?/)
  return match?.[1] ?? null
}

export async function downloadScholarshipResultsExport(
  scholarshipId: string,
  format: "xlsx" | "pdf",
): Promise<void> {
  const response = await api.get<Blob>(`/admin/scholarships/${scholarshipId}/results/export`, {
    params: { format },
    responseType: "blob",
  })

  const filename =
    getFilenameFromContentDisposition(response.headers["content-disposition"]) ??
    `scholarship-results.${format}`
  const blob = response.data instanceof Blob ? response.data : new Blob([response.data])
  const objectUrl = window.URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(objectUrl)
}
