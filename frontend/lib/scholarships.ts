import api from "@/lib/api"
import type {
  Column,
  ColumnInput,
  JuryMember,
  Scholarship,
  ScholarshipDetail,
  ScholarshipInput,
  ScholarshipStatus,
} from "@/types"

export type ListScholarshipsParams = {
  status?: ScholarshipStatus
  search?: string
  skip?: number
  limit?: number
}

export async function listScholarships(params: ListScholarshipsParams = {}): Promise<Scholarship[]> {
  const { data } = await api.get<Scholarship[]>("/scholarships", { params })
  return data
}

export async function getScholarship(scholarshipId: string): Promise<ScholarshipDetail> {
  const { data } = await api.get<ScholarshipDetail>(`/scholarships/${scholarshipId}`)
  return data
}

export async function createScholarship(payload: ScholarshipInput): Promise<Scholarship> {
  const { data } = await api.post<Scholarship>("/scholarships", payload)
  return data
}

export async function updateScholarship(scholarshipId: string, payload: Partial<ScholarshipInput>): Promise<Scholarship> {
  const { data } = await api.patch<Scholarship>(`/scholarships/${scholarshipId}`, payload)
  return data
}

export async function changeScholarshipStatus(
  scholarshipId: string,
  status: ScholarshipStatus,
): Promise<Scholarship> {
  const { data } = await api.patch<Scholarship>(`/scholarships/${scholarshipId}/status`, { status })
  return data
}

export async function listScholarshipColumns(scholarshipId: string): Promise<Column[]> {
  const { data } = await api.get<Column[]>(`/scholarships/${scholarshipId}/columns`)
  return data
}

export async function createScholarshipColumn(scholarshipId: string, payload: ColumnInput): Promise<Column> {
  const { data } = await api.post<Column>(`/scholarships/${scholarshipId}/columns`, payload)
  return data
}

export async function updateScholarshipColumn(
  scholarshipId: string,
  columnId: string,
  payload: Partial<ColumnInput>,
): Promise<Column> {
  const { data } = await api.patch<Column>(`/scholarships/${scholarshipId}/columns/${columnId}`, payload)
  return data
}

export async function deleteScholarshipColumn(scholarshipId: string, columnId: string): Promise<void> {
  await api.delete(`/scholarships/${scholarshipId}/columns/${columnId}`)
}

export async function reorderScholarshipColumns(scholarshipId: string, order: string[]): Promise<void> {
  await api.patch(`/scholarships/${scholarshipId}/columns/reorder`, { order })
}

export async function listScholarshipJury(scholarshipId: string): Promise<JuryMember[]> {
  const { data } = await api.get<JuryMember[]>(`/scholarships/${scholarshipId}/jury`)
  return data
}

export async function assignScholarshipJury(scholarshipId: string, juryId: string): Promise<void> {
  await api.post(`/scholarships/${scholarshipId}/jury`, { jury_id: juryId })
}

export async function removeScholarshipJury(scholarshipId: string, juryId: string): Promise<void> {
  await api.delete(`/scholarships/${scholarshipId}/jury/${juryId}`)
}
