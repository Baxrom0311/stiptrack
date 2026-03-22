import api from "@/lib/api"
import type {
  Scholarship,
  ScholarshipTemplate,
  ScholarshipTemplateCreateInput,
  ScholarshipTemplateInstantiateInput,
} from "@/types"

export async function listScholarshipTemplates(): Promise<ScholarshipTemplate[]> {
  const { data } = await api.get<ScholarshipTemplate[]>("/scholarship-templates")
  return data
}

export async function createScholarshipTemplate(
  payload: ScholarshipTemplateCreateInput,
): Promise<ScholarshipTemplate> {
  const { data } = await api.post<ScholarshipTemplate>("/scholarship-templates", payload)
  return data
}

export async function instantiateScholarshipTemplate(
  templateId: string,
  payload: ScholarshipTemplateInstantiateInput,
): Promise<Scholarship> {
  const { data } = await api.post<Scholarship>(`/scholarship-templates/${templateId}/instantiate`, payload)
  return data
}
