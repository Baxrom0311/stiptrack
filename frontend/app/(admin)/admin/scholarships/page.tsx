"use client"

import Link from "next/link"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { CalendarRange, CopyPlus, Plus, Save, Settings2, Trophy, Users, Workflow } from "lucide-react"
import { useEffect, useMemo, useState } from "react"

import { listScholarshipApplications } from "@/lib/applications"
import { createStage, deleteStage, listStages } from "@/lib/stages"
import { createScholarshipTemplate, instantiateScholarshipTemplate, listScholarshipTemplates } from "@/lib/templates"
import {
  assignScholarshipJury,
  changeScholarshipStatus,
  createScholarship,
  createScholarshipColumn,
  deleteScholarshipColumn,
  getScholarship,
  listScholarshipJury,
  listScholarships,
  reorderScholarshipColumns,
  removeScholarshipJury,
  updateScholarship,
} from "@/lib/scholarships"
import {
  columnFormSchema,
  FieldErrors,
  getFieldErrors,
  getFirstFieldError,
  juryAssignmentSchema,
  scholarshipFormSchema,
  scholarshipTemplateFormSchema,
  scholarshipTemplateInstantiateSchema,
  stageFormSchema,
} from "@/lib/form-validation"
import { listUsers } from "@/lib/users"
import { extractErrorMessage, notifyError, notifySuccess } from "@/lib/notifications"

import ColumnBuilder from "@/components/scholarship/ColumnBuilder"
import StatusBadge from "@/components/scholarship/StatusBadge"
import { Badge } from "@/components/ui/badge"
import { buttonVariants, Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import EmptyState from "@/components/ui/empty-state"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { DetailPageSkeleton, FormCardSkeleton, HeroSkeleton, ListCardsSkeleton } from "@/components/ui/page-skeletons"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import type {
  AIProvider,
  ApplicationListItem,
  ColumnInput,
  FieldType,
  ScholarshipDetail,
  ScholarshipInput,
  ScholarshipStageType,
  ScholarshipStatus,
  SuggestedColumn,
  WorkflowStage,
  WorkflowStageInput,
} from "@/types"

type ScholarshipFormState = {
  title: string
  description: string
  deadline: string
  ai_analysis_enabled: boolean
  blind_review_enabled: boolean
  ai_provider: AIProvider
  ai_model: string
  max_winners: number
}

type ColumnFormState = {
  name: string
  description: string
  field_type: FieldType
  select_options_text: string
  is_required: boolean
  ai_analyze: boolean
  max_score: number
  input_min: number | null
  input_max: number | null
}

type StageFormState = {
  name: string
  stage_type: ScholarshipStageType
  description: string
  starts_at: string
  ends_at: string
  is_required: boolean
  is_active: boolean
}

type TemplateFormState = {
  name: string
  description: string
}

type TemplateInstantiateFormState = {
  template_id: string
  title: string
  description: string
  deadline: string
  starts_at: string
}

type ScholarshipListFilter = "all" | ScholarshipStatus

const STAGE_TYPE_OPTIONS: Array<{ value: ScholarshipStageType; label: string }> = [
  { value: "application", label: "Document Upload" },
  { value: "review", label: "Review" },
  { value: "exam", label: "Exam" },
  { value: "interview", label: "Interview" },
  { value: "final_decision", label: "Final Decision" },
  { value: "appeal", label: "Appeal" },
]

const STATUS_OPTIONS: Array<{ value: ScholarshipStatus; label: string; hint: string }> = [
  { value: "draft", label: "Draft", hint: "Tayyorlash bosqichi, student ko‘rmaydi." },
  { value: "open", label: "Open", hint: "Arizalar qabul qilinadi." },
  { value: "closed", label: "Closed", hint: "Ariza yopilgan, ko‘rib chiqish ketadi." },
  { value: "done", label: "Done", hint: "Yakunlangan, natijalar va appeal ochiq." },
]

const AI_PROVIDER_OPTIONS: Array<{ value: AIProvider; label: string; hint: string }> = [
  { value: "claude", label: "Claude", hint: "Anthropic oilasi" },
  { value: "openai", label: "OpenAI", hint: "GPT oilasi" },
  { value: "gemini", label: "Gemini", hint: "Google Gemini" },
  { value: "ollama", label: "Ollama", hint: "Lokal/self-hosted" },
  { value: "deepseek", label: "DeepSeek", hint: "DeepSeek API" },
]

const EMPTY_SCHOLARSHIP_FORM: ScholarshipFormState = {
  title: "",
  description: "",
  deadline: "",
  ai_analysis_enabled: false,
  blind_review_enabled: false,
  ai_provider: "claude",
  ai_model: "",
  max_winners: 1,
}

const EMPTY_COLUMN_FORM: ColumnFormState = {
  name: "",
  description: "",
  field_type: "text",
  select_options_text: "",
  is_required: true,
  ai_analyze: false,
  max_score: 10,
  input_min: null,
  input_max: null,
}

const EMPTY_STAGE_FORM: StageFormState = {
  name: "",
  stage_type: "application",
  description: "",
  starts_at: "",
  ends_at: "",
  is_required: true,
  is_active: true,
}

const EMPTY_TEMPLATE_FORM: TemplateFormState = {
  name: "",
  description: "",
}

const EMPTY_TEMPLATE_INSTANTIATE_FORM: TemplateInstantiateFormState = {
  template_id: "",
  title: "",
  description: "",
  deadline: "",
  starts_at: "",
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "-"
  }
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }
  return new Intl.DateTimeFormat("uz-UZ", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed)
}

function toDateTimeLocal(value: string | null | undefined): string {
  if (!value) {
    return ""
  }
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return ""
  }
  const local = new Date(parsed.getTime() - parsed.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 16)
}

function toIsoOrNull(value: string): string | null {
  if (!value.trim()) {
    return null
  }
  return new Date(value).toISOString()
}

function formatAiConfig(provider: AIProvider, model?: string | null): string {
  const providerLabel = AI_PROVIDER_OPTIONS.find((item) => item.value === provider)?.label ?? provider
  return model?.trim() ? `${providerLabel} / ${model.trim()}` : providerLabel
}

function buildScholarshipPayload(form: ScholarshipFormState): ScholarshipInput {
  return {
    title: form.title.trim(),
    description: form.description.trim() || null,
    deadline: toIsoOrNull(form.deadline),
    ai_analysis_enabled: form.ai_analysis_enabled,
    blind_review_enabled: form.blind_review_enabled,
    ai_provider: form.ai_provider,
    ai_model: form.ai_model.trim() || null,
    max_winners: Math.max(1, Number(form.max_winners) || 1),
  }
}

function buildColumnPayload(form: ColumnFormState): ColumnInput {
  return {
    name: form.name.trim(),
    description: form.description.trim() || null,
    field_type: form.field_type,
    select_options:
      form.field_type === "select"
        ? form.select_options_text
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean)
        : null,
    is_required: form.is_required,
    ai_analyze: form.ai_analyze,
    max_score: Math.max(0, Number(form.max_score) || 0),
    input_min: form.field_type === "number" ? form.input_min : null,
    input_max: form.field_type === "number" ? form.input_max : null,
  }
}

function buildStagePayload(form: StageFormState): WorkflowStageInput {
  return {
    name: form.name.trim(),
    stage_type: form.stage_type,
    description: form.description.trim() || null,
    starts_at: new Date(form.starts_at).toISOString(),
    ends_at: new Date(form.ends_at).toISOString(),
    is_required: form.is_required,
    is_active: form.is_active,
    config: null,
  }
}

function buildTemplateInstantiatePayload(form: TemplateInstantiateFormState) {
  return {
    title: form.title.trim(),
    description: form.description.trim() || null,
    deadline: toIsoOrNull(form.deadline),
    starts_at: toIsoOrNull(form.starts_at),
  }
}

function applicationStatusLabel(status: ApplicationListItem["status"]): string {
  if (status === "draft") {
    return "Draft"
  }
  if (status === "submitted") {
    return "Submitted"
  }
  if (status === "in_review") {
    return "In Review"
  }
  if (status === "winner") {
    return "Winner"
  }
  if (status === "rejected") {
    return "Rejected"
  }
  return status
}

function stageTypeLabel(value: ScholarshipStageType): string {
  return STAGE_TYPE_OPTIONS.find((option) => option.value === value)?.label ?? value
}

function getStatusValidation(
  scholarship: ScholarshipDetail,
  targetStatus: ScholarshipStatus,
  stages: WorkflowStage[],
  juryCount: number,
  applicationCount: number,
): { errors: string[]; warnings: string[] } {
  const errors: string[] = []
  const warnings: string[] = []
  const hasApplicationStage = stages.some((stage) => stage.stage_type === "application" && stage.is_active)
  const hasReviewStage = stages.some((stage) => stage.stage_type === "review" && stage.is_active)
  const hasFinalDecisionStage = stages.some((stage) => stage.stage_type === "final_decision" && stage.is_active)

  if (targetStatus === "open") {
    if (!scholarship.deadline) {
      errors.push("Open holatiga o‘tkazish uchun deadline kiritilishi kerak.")
    }
    if (scholarship.columns.length === 0) {
      errors.push("Open holatiga o‘tishdan oldin kamida bitta column qo‘shilishi kerak.")
    }
    if (!hasApplicationStage) {
      errors.push("Open holati uchun active `application` bosqichi bo‘lishi kerak.")
    }
    if (juryCount === 0) {
      warnings.push("Hozircha birorta ham hakam biriktirilmagan.")
    }
    if (!scholarship.nizom_file_url) {
      warnings.push("Nizom fayli yuklanmagan. Student detail sahifasida faqat qo‘lda kiritilgan ma’lumotlar ko‘rinadi.")
    }
  }

  if (targetStatus === "closed") {
    if (!hasReviewStage && !hasFinalDecisionStage) {
      warnings.push("Ko‘rib chiqish yoki final qaror bosqichi belgilanmagan.")
    }
    if (applicationCount === 0) {
      warnings.push("Hozircha arizalar yo‘q. Closed holatga o‘tkazsangiz topshirishlar to‘xtaydi.")
    }
  }

  if (targetStatus === "done") {
    if (!hasFinalDecisionStage) {
      errors.push("Done holati uchun active `final_decision` bosqichi tavsiya emas, majburiy hisoblanadi.")
    }
    if (applicationCount === 0) {
      warnings.push("Arizalarsiz yakunlash odatiy emas. Natijalar sahifasi bo‘sh qoladi.")
    }
  }

  return { errors, warnings }
}

export default function AdminScholarshipsPage() {
  const queryClient = useQueryClient()

  const [selectedScholarshipId, setSelectedScholarshipId] = useState("")
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<ScholarshipListFilter>("all")
  const [pendingStatus, setPendingStatus] = useState<ScholarshipStatus | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [createFromTemplateOpen, setCreateFromTemplateOpen] = useState(false)
  const [saveTemplateOpen, setSaveTemplateOpen] = useState(false)
  const [createForm, setCreateForm] = useState<ScholarshipFormState>(EMPTY_SCHOLARSHIP_FORM)
  const [editForm, setEditForm] = useState<ScholarshipFormState>(EMPTY_SCHOLARSHIP_FORM)
  const [columnForm, setColumnForm] = useState<ColumnFormState>(EMPTY_COLUMN_FORM)
  const [stageForm, setStageForm] = useState<StageFormState>(EMPTY_STAGE_FORM)
  const [templateForm, setTemplateForm] = useState<TemplateFormState>(EMPTY_TEMPLATE_FORM)
  const [templateInstantiateForm, setTemplateInstantiateForm] = useState<TemplateInstantiateFormState>(
    EMPTY_TEMPLATE_INSTANTIATE_FORM,
  )
  const [selectedJuryId, setSelectedJuryId] = useState("")
  const [importedColumns, setImportedColumns] = useState<SuggestedColumn[]>([])
  const [createErrors, setCreateErrors] = useState<FieldErrors<keyof ScholarshipFormState>>({})
  const [editErrors, setEditErrors] = useState<FieldErrors<keyof ScholarshipFormState>>({})
  const [columnErrors, setColumnErrors] = useState<FieldErrors<keyof ColumnFormState>>({})
  const [stageErrors, setStageErrors] = useState<FieldErrors<keyof StageFormState>>({})
  const [templateErrors, setTemplateErrors] = useState<FieldErrors<keyof TemplateFormState>>({})
  const [templateInstantiateErrors, setTemplateInstantiateErrors] =
    useState<FieldErrors<keyof TemplateInstantiateFormState>>({})
  const [juryError, setJuryError] = useState<string | null>(null)
  const [createFormError, setCreateFormError] = useState<string | null>(null)
  const [editFormError, setEditFormError] = useState<string | null>(null)
  const [columnFormError, setColumnFormError] = useState<string | null>(null)
  const [stageFormError, setStageFormError] = useState<string | null>(null)
  const [templateFormError, setTemplateFormError] = useState<string | null>(null)
  const [templateInstantiateFormError, setTemplateInstantiateFormError] = useState<string | null>(null)

  const scholarshipsQuery = useQuery({
    queryKey: ["admin-scholarships"],
    queryFn: () => listScholarships({ limit: 200 }),
    retry: 0,
  })

  const templatesQuery = useQuery({
    queryKey: ["scholarship-templates"],
    queryFn: listScholarshipTemplates,
    retry: 0,
  })

  const detailQuery = useQuery({
    queryKey: ["admin-scholarship-detail", selectedScholarshipId],
    queryFn: () => getScholarship(selectedScholarshipId),
    enabled: Boolean(selectedScholarshipId),
    retry: 0,
  })

  const juryQuery = useQuery({
    queryKey: ["admin-scholarship-jury", selectedScholarshipId],
    queryFn: () => listScholarshipJury(selectedScholarshipId),
    enabled: Boolean(selectedScholarshipId),
    retry: 0,
  })

  const juryUsersQuery = useQuery({
    queryKey: ["admin-jury-users"],
    queryFn: () => listUsers({ role: "jury", limit: 200 }),
    retry: 0,
  })

  const applicationsQuery = useQuery({
    queryKey: ["admin-scholarship-applications", selectedScholarshipId],
    queryFn: () => listScholarshipApplications(selectedScholarshipId, { limit: 200 }),
    enabled: Boolean(selectedScholarshipId),
    retry: 0,
  })

  const stagesQuery = useQuery({
    queryKey: ["admin-scholarship-stages", selectedScholarshipId],
    queryFn: () => listStages(selectedScholarshipId),
    enabled: Boolean(selectedScholarshipId),
    retry: 0,
  })

  useEffect(() => {
    if (!selectedScholarshipId && scholarshipsQuery.data && scholarshipsQuery.data.length > 0) {
      setSelectedScholarshipId(scholarshipsQuery.data[0].id)
    }
  }, [scholarshipsQuery.data, selectedScholarshipId])

  useEffect(() => {
    if (!detailQuery.data) {
      return
    }
    setEditForm({
      title: detailQuery.data.title,
      description: detailQuery.data.description ?? "",
      deadline: toDateTimeLocal(detailQuery.data.deadline),
      ai_analysis_enabled: detailQuery.data.ai_analysis_enabled,
      blind_review_enabled: detailQuery.data.blind_review_enabled,
      ai_provider: detailQuery.data.ai_provider,
      ai_model: detailQuery.data.ai_model ?? "",
      max_winners: detailQuery.data.max_winners,
    })
    setEditErrors({})
    setEditFormError(null)
  }, [detailQuery.data])

  useEffect(() => {
    if (!detailQuery.data) {
      return
    }
    setTemplateForm({
      name: `${detailQuery.data.title} template`,
      description: detailQuery.data.description ?? "",
    })
  }, [detailQuery.data])

  useEffect(() => {
    setImportedColumns([])
    setSelectedJuryId("")
    setJuryError(null)
    setColumnErrors({})
    setColumnFormError(null)
    setStageErrors({})
    setStageFormError(null)
    setPendingStatus(null)
  }, [selectedScholarshipId])

  const setCreateField = <K extends keyof ScholarshipFormState>(field: K, value: ScholarshipFormState[K]) => {
    setCreateForm((prev) => ({ ...prev, [field]: value }))
    setCreateErrors((prev) => ({ ...prev, [field]: undefined }))
    setCreateFormError(null)
  }

  const setEditField = <K extends keyof ScholarshipFormState>(field: K, value: ScholarshipFormState[K]) => {
    setEditForm((prev) => ({ ...prev, [field]: value }))
    setEditErrors((prev) => ({ ...prev, [field]: undefined }))
    setEditFormError(null)
  }

  const setColumnField = <K extends keyof ColumnFormState>(field: K, value: ColumnFormState[K]) => {
    setColumnForm((prev) => ({ ...prev, [field]: value }))
    setColumnErrors((prev) => ({ ...prev, [field]: undefined }))
    setColumnFormError(null)
  }

  const setStageField = <K extends keyof StageFormState>(field: K, value: StageFormState[K]) => {
    setStageForm((prev) => ({ ...prev, [field]: value }))
    setStageErrors((prev) => ({ ...prev, [field]: undefined }))
    setStageFormError(null)
  }

  const setTemplateField = <K extends keyof TemplateFormState>(field: K, value: TemplateFormState[K]) => {
    setTemplateForm((prev) => ({ ...prev, [field]: value }))
    setTemplateErrors((prev) => ({ ...prev, [field]: undefined }))
    setTemplateFormError(null)
  }

  const setTemplateInstantiateField = <K extends keyof TemplateInstantiateFormState>(
    field: K,
    value: TemplateInstantiateFormState[K],
  ) => {
    setTemplateInstantiateForm((prev) => ({ ...prev, [field]: value }))
    setTemplateInstantiateErrors((prev) => ({ ...prev, [field]: undefined }))
    setTemplateInstantiateFormError(null)
  }

  const filteredScholarships = useMemo(() => {
    const items = scholarshipsQuery.data ?? []
    const normalized = search.trim().toLowerCase()
    return items.filter((item) => {
      const matchesSearch = !normalized || item.title.toLowerCase().includes(normalized)
      const matchesStatus = statusFilter === "all" || item.status === statusFilter
      return matchesSearch && matchesStatus
    })
  }, [scholarshipsQuery.data, search, statusFilter])
  const hasScholarships = (scholarshipsQuery.data?.length ?? 0) > 0

  const availableJuryUsers = useMemo(() => {
    const assignedIds = new Set((juryQuery.data ?? []).map((user) => user.id))
    return (juryUsersQuery.data ?? []).filter((user) => !assignedIds.has(user.id))
  }, [juryQuery.data, juryUsersQuery.data])

  const selectedTemplate = useMemo(
    () => (templatesQuery.data ?? []).find((item) => item.id === templateInstantiateForm.template_id) ?? null,
    [templateInstantiateForm.template_id, templatesQuery.data],
  )

  const createScholarshipMutation = useMutation({
    mutationFn: async () => {
      const parsed = scholarshipFormSchema.safeParse(createForm)
      if (!parsed.success) {
        const errors = getFieldErrors<keyof ScholarshipFormState>(parsed.error)
        setCreateErrors(errors)
        throw new Error(getFirstFieldError(errors) ?? "Scholarship formasi noto‘g‘ri to‘ldirilgan.")
      }

      setCreateErrors({})
      setCreateFormError(null)
      return createScholarship(buildScholarshipPayload(parsed.data))
    },
    onSuccess: async (scholarship) => {
      notifySuccess(`Scholarship yaratildi: ${scholarship.title}`)
      setCreateOpen(false)
      setCreateForm(EMPTY_SCHOLARSHIP_FORM)
      setCreateErrors({})
      setCreateFormError(null)
      setSelectedScholarshipId(scholarship.id)
      await queryClient.invalidateQueries({ queryKey: ["admin-scholarships"] })
    },
    onError: (error) => {
      const message = extractErrorMessage(error)
      setCreateFormError(message)
      notifyError(message)
    },
  })

  const updateScholarshipMutation = useMutation({
    mutationFn: async () => {
      const parsed = scholarshipFormSchema.safeParse(editForm)
      if (!parsed.success) {
        const errors = getFieldErrors<keyof ScholarshipFormState>(parsed.error)
        setEditErrors(errors)
        throw new Error(getFirstFieldError(errors) ?? "Scholarship formasi noto‘g‘ri to‘ldirilgan.")
      }

      setEditErrors({})
      setEditFormError(null)
      return updateScholarship(selectedScholarshipId, buildScholarshipPayload(parsed.data))
    },
    onSuccess: async () => {
      setEditFormError(null)
      notifySuccess("Scholarship asosiy ma'lumotlari yangilandi.")
      await queryClient.invalidateQueries({ queryKey: ["admin-scholarship-detail", selectedScholarshipId] })
      await queryClient.invalidateQueries({ queryKey: ["admin-scholarships"] })
    },
    onError: (error) => {
      const message = extractErrorMessage(error)
      setEditFormError(message)
      notifyError(message)
    },
  })

  const importColumnsMutation = useMutation({
    mutationFn: async () => {
      for (const column of importedColumns.sort((left, right) => left.order_index - right.order_index)) {
        await createScholarshipColumn(selectedScholarshipId, {
          name: column.name,
          description: column.description,
          field_type: column.field_type,
          select_options: column.select_options ?? null,
          is_required: column.is_required,
          ai_analyze: column.ai_analyze,
          max_score: column.max_score,
          input_min: column.input_min ?? null,
          input_max: column.input_max ?? null,
        })
      }
    },
    onSuccess: async () => {
      notifySuccess(`${importedColumns.length} ta AI ustuni qo‘shildi.`)
      setImportedColumns([])
      await queryClient.invalidateQueries({ queryKey: ["admin-scholarship-detail", selectedScholarshipId] })
    },
    onError: (error) => {
      notifyError(error)
    },
  })

  const createColumnMutation = useMutation({
    mutationFn: async () => {
      const parsed = columnFormSchema.safeParse(columnForm)
      if (!parsed.success) {
        const errors = getFieldErrors<keyof ColumnFormState>(parsed.error)
        setColumnErrors(errors)
        throw new Error(getFirstFieldError(errors) ?? "Column formasi noto‘g‘ri to‘ldirilgan.")
      }

      setColumnErrors({})
      setColumnFormError(null)
      return createScholarshipColumn(selectedScholarshipId, buildColumnPayload(parsed.data))
    },
    onSuccess: async () => {
      notifySuccess("Yangi ustun qo‘shildi.")
      setColumnForm(EMPTY_COLUMN_FORM)
      setColumnErrors({})
      setColumnFormError(null)
      await queryClient.invalidateQueries({ queryKey: ["admin-scholarship-detail", selectedScholarshipId] })
    },
    onError: (error) => {
      const message = extractErrorMessage(error)
      setColumnFormError(message)
      notifyError(message)
    },
  })

  const deleteColumnMutation = useMutation({
    mutationFn: (columnId: string) => deleteScholarshipColumn(selectedScholarshipId, columnId),
    onSuccess: async () => {
      notifySuccess("Ustun o‘chirildi.")
      await queryClient.invalidateQueries({ queryKey: ["admin-scholarship-detail", selectedScholarshipId] })
    },
    onError: (error) => {
      notifyError(error)
    },
  })

  const reorderColumnsMutation = useMutation({
    mutationFn: (order: string[]) => reorderScholarshipColumns(selectedScholarshipId, order),
    onSuccess: async () => {
      notifySuccess("Ustunlar tartibi yangilandi.")
      await queryClient.invalidateQueries({ queryKey: ["admin-scholarship-detail", selectedScholarshipId] })
    },
    onError: (error) => {
      notifyError(error)
    },
  })

  const assignJuryMutation = useMutation({
    mutationFn: async () => {
      const parsed = juryAssignmentSchema.safeParse({ jury_id: selectedJuryId })
      if (!parsed.success) {
        const message = getFirstFieldError(getFieldErrors<"jury_id">(parsed.error)) ?? "Hakam tanlash shart."
        setJuryError(message)
        throw new Error(message)
      }

      setJuryError(null)
      return assignScholarshipJury(selectedScholarshipId, parsed.data.jury_id)
    },
    onSuccess: async () => {
      notifySuccess("Hakam biriktirildi.")
      setSelectedJuryId("")
      setJuryError(null)
      await queryClient.invalidateQueries({ queryKey: ["admin-scholarship-jury", selectedScholarshipId] })
    },
    onError: (error) => {
      const message = extractErrorMessage(error)
      setJuryError(message)
      notifyError(message)
    },
  })

  const removeJuryMutation = useMutation({
    mutationFn: (juryId: string) => removeScholarshipJury(selectedScholarshipId, juryId),
    onSuccess: async () => {
      notifySuccess("Hakam chiqarildi.")
      await queryClient.invalidateQueries({ queryKey: ["admin-scholarship-jury", selectedScholarshipId] })
    },
    onError: (error) => {
      notifyError(error)
    },
  })

  const changeStatusMutation = useMutation({
    mutationFn: (status: ScholarshipStatus) => changeScholarshipStatus(selectedScholarshipId, status),
    onSuccess: async (scholarship) => {
      notifySuccess(`Scholarship status: ${scholarship.status}`)
      await queryClient.invalidateQueries({ queryKey: ["admin-scholarship-detail", selectedScholarshipId] })
      await queryClient.invalidateQueries({ queryKey: ["admin-scholarships"] })
    },
    onError: (error) => {
      notifyError(error)
    },
  })

  const createStageMutation = useMutation({
    mutationFn: async () => {
      const parsed = stageFormSchema.safeParse(stageForm)
      if (!parsed.success) {
        const errors = getFieldErrors<keyof StageFormState>(parsed.error)
        setStageErrors(errors)
        throw new Error(getFirstFieldError(errors) ?? "Stage formasi noto‘g‘ri to‘ldirilgan.")
      }

      setStageErrors({})
      setStageFormError(null)
      return createStage(selectedScholarshipId, buildStagePayload(parsed.data))
    },
    onSuccess: async () => {
      notifySuccess("Bosqich qo‘shildi.")
      setStageForm(EMPTY_STAGE_FORM)
      setStageErrors({})
      setStageFormError(null)
      await queryClient.invalidateQueries({ queryKey: ["admin-scholarship-stages", selectedScholarshipId] })
    },
    onError: (error) => {
      const message = extractErrorMessage(error)
      setStageFormError(message)
      notifyError(message)
    },
  })

  const saveTemplateMutation = useMutation({
    mutationFn: async () => {
      if (!selectedScholarshipId) {
        throw new Error("Avval scholarship tanlash kerak.")
      }

      const parsed = scholarshipTemplateFormSchema.safeParse(templateForm)
      if (!parsed.success) {
        const errors = getFieldErrors<keyof TemplateFormState>(parsed.error)
        setTemplateErrors(errors)
        throw new Error(getFirstFieldError(errors) ?? "Template formasi noto‘g‘ri to‘ldirilgan.")
      }

      setTemplateErrors({})
      setTemplateFormError(null)
      return createScholarshipTemplate({
        scholarship_id: selectedScholarshipId,
        name: parsed.data.name,
        description: parsed.data.description || null,
      })
    },
    onSuccess: async (template) => {
      notifySuccess(`Template saqlandi: ${template.name}`)
      setSaveTemplateOpen(false)
      await queryClient.invalidateQueries({ queryKey: ["scholarship-templates"] })
    },
    onError: (error) => {
      const message = extractErrorMessage(error)
      setTemplateFormError(message)
      notifyError(message)
    },
  })

  const instantiateTemplateMutation = useMutation({
    mutationFn: async () => {
      const parsed = scholarshipTemplateInstantiateSchema.safeParse(templateInstantiateForm)
      if (!parsed.success) {
        const errors = getFieldErrors<keyof TemplateInstantiateFormState>(parsed.error)
        setTemplateInstantiateErrors(errors)
        throw new Error(getFirstFieldError(errors) ?? "Template yaratish formasi noto‘g‘ri.")
      }

      setTemplateInstantiateErrors({})
      setTemplateInstantiateFormError(null)
      return instantiateScholarshipTemplate(
        parsed.data.template_id,
        buildTemplateInstantiatePayload(parsed.data),
      )
    },
    onSuccess: async (scholarship) => {
      notifySuccess(`Template asosida scholarship yaratildi: ${scholarship.title}`)
      setCreateFromTemplateOpen(false)
      setTemplateInstantiateForm(EMPTY_TEMPLATE_INSTANTIATE_FORM)
      setSelectedScholarshipId(scholarship.id)
      await queryClient.invalidateQueries({ queryKey: ["admin-scholarships"] })
      await queryClient.invalidateQueries({ queryKey: ["admin-scholarship-detail", scholarship.id] })
    },
    onError: (error) => {
      const message = extractErrorMessage(error)
      setTemplateInstantiateFormError(message)
      notifyError(message)
    },
  })

  const deleteStageMutation = useMutation({
    mutationFn: (stageId: string) => deleteStage(selectedScholarshipId, stageId),
    onSuccess: async () => {
      notifySuccess("Bosqich o‘chirildi.")
      await queryClient.invalidateQueries({ queryKey: ["admin-scholarship-stages", selectedScholarshipId] })
    },
    onError: (error) => {
      notifyError(error)
    },
  })

  const selectedScholarship = detailQuery.data
  const pendingStatusValidation = useMemo(() => {
    if (!selectedScholarship || !pendingStatus) {
      return { errors: [], warnings: [] }
    }
    return getStatusValidation(
      selectedScholarship,
      pendingStatus,
      stagesQuery.data ?? [],
      (juryQuery.data ?? []).length,
      (applicationsQuery.data ?? []).length,
    )
  }, [applicationsQuery.data, juryQuery.data, pendingStatus, selectedScholarship, stagesQuery.data])

  if (scholarshipsQuery.isLoading) {
    return (
      <div className="grid gap-6">
        <HeroSkeleton />
        <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
          <ListCardsSkeleton count={5} />
          <DetailPageSkeleton className="xl:grid-cols-1" />
        </div>
      </div>
    )
  }

  if (selectedScholarshipId && detailQuery.isLoading) {
    return (
      <div className="grid gap-6">
        <HeroSkeleton />
        <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
          <FormCardSkeleton fields={1} actions={0} />
          <DetailPageSkeleton className="xl:grid-cols-1" />
        </div>
      </div>
    )
  }

  return (
    <div className="grid gap-6">
      <section className="rounded-3xl bg-[linear-gradient(135deg,_#fff7ed,_#fef3c7_45%,_#eff6ff)] p-6 ring-1 ring-amber-200">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <Badge variant="outline">Scholarship Control</Badge>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Stipendiya boshqaruvi</h1>
            <p className="max-w-3xl text-sm text-slate-700">
              Bir sahifada scholarship yaratish, nizom asosida AI ustun chiqarish, hakam biriktirish, bosqichlarni
              boshqarish va yakuniy oqimni nazorat qilish.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link href="/admin/results">
              <Button type="button" variant="outline">
                <Trophy className="mr-2 h-4 w-4" />
                Results
              </Button>
            </Link>
            <Button type="button" variant="outline" onClick={() => setCreateFromTemplateOpen(true)}>
              <CopyPlus className="mr-2 h-4 w-4" />
              Template asosida
            </Button>
            <Button type="button" onClick={() => setCreateOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Yangi scholarship
            </Button>
          </div>
        </div>
      </section>
      <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle>Scholarshiplar</CardTitle>
            <CardDescription>Mavjud grantlar ro‘yxati. Tanlab, o‘ng tomonda boshqaring.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Qidirish..." />
            <select
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as ScholarshipListFilter)}
            >
              <option value="all">Barcha statuslar</option>
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            <div className="overflow-hidden rounded-2xl border border-slate-200">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Scholarship</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Deadline</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredScholarships.map((scholarship) => (
                    <TableRow
                      key={scholarship.id}
                      onClick={() => setSelectedScholarshipId(scholarship.id)}
                      className={cn(
                        "cursor-pointer",
                        selectedScholarshipId === scholarship.id && "bg-slate-100 hover:bg-slate-100",
                      )}
                    >
                      <TableCell>
                        <div className="min-w-0">
                          <p className="truncate font-medium text-slate-900">{scholarship.title}</p>
                          <p className="truncate text-xs text-slate-500">{scholarship.description || "Tavsif kiritilmagan."}</p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={scholarship.status} />
                      </TableCell>
                      <TableCell className="text-right text-xs text-slate-500">{formatDate(scholarship.deadline)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {!scholarshipsQuery.isLoading && filteredScholarships.length === 0 && (
              <EmptyState
                title={hasScholarships ? "Mos scholarship topilmadi" : "Scholarshiplar hali yo‘q"}
                description={
                  hasScholarships
                    ? "Qidiruv yoki status filter bo‘yicha hech qanday stipendiya topilmadi."
                    : "Yangi stipendiya yaratganingizdan keyin ular shu ro‘yxatda ko‘rinadi."
                }
                action={
                  hasScholarships ? (
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        setSearch("")
                        setStatusFilter("all")
                      }}
                    >
                      Filterlarni tozalash
                    </Button>
                  ) : (
                    <Button type="button" onClick={() => setCreateOpen(true)}>
                      Yangi scholarship
                    </Button>
                  )
                }
              />
            )}
          </CardContent>
        </Card>

        {!selectedScholarshipId ? (
          <Card className="border-slate-200">
            <CardContent className="pt-6">
              <EmptyState
                title="Scholarship tanlanmagan"
                description="Chap tomondan bir stipendiyani tanlang yoki yangi scholarship yaratib boshqarishni boshlang."
                action={
                  <Button type="button" onClick={() => setCreateOpen(true)}>
                    Yangi scholarship
                  </Button>
                }
              />
            </CardContent>
          </Card>
        ) : detailQuery.isError || !selectedScholarship ? (
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle>Scholarship ma’lumotini yuklab bo‘lmadi</CardTitle>
              <CardDescription>Endpoint yoki ruxsat bilan bog‘liq xatolik yuz berdi.</CardDescription>
            </CardHeader>
          </Card>
        ) : (
          <Card className="border-slate-200">
            <CardHeader>
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <CardTitle>{selectedScholarship.title}</CardTitle>
                    <StatusBadge status={selectedScholarship.status} />
                  </div>
                  <CardDescription className="mt-2">
                    {selectedScholarship.description || "Tavsif hali kiritilmagan."}
                  </CardDescription>
                </div>

                <div className="grid gap-2 text-right text-xs text-slate-500">
                  <Button type="button" variant="outline" size="sm" onClick={() => setSaveTemplateOpen(true)}>
                    <Save className="mr-2 h-4 w-4" />
                    Template saqlash
                  </Button>
                  <span>Deadline: {formatDate(selectedScholarship.deadline)}</span>
                  <span>Columns: {selectedScholarship.columns.length}</span>
                  <span>AI: {formatAiConfig(selectedScholarship.ai_provider, selectedScholarship.ai_model)}</span>
                  <span>Blind review: {selectedScholarship.blind_review_enabled ? "On" : "Off"}</span>
                  <span>Max winners: {selectedScholarship.max_winners}</span>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="info">
                <TabsList variant="line">
                  <TabsTrigger value="info">Info</TabsTrigger>
                  <TabsTrigger value="workflow">Workflow</TabsTrigger>
                  <TabsTrigger value="columns">Nizom & Columns</TabsTrigger>
                  <TabsTrigger value="jury">Jury</TabsTrigger>
                  <TabsTrigger value="applications">Applications</TabsTrigger>
                  <TabsTrigger value="status">Status</TabsTrigger>
                </TabsList>

                <TabsContent value="info" className="pt-6">
                  <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
                    <div className="space-y-4">
                      {editFormError && <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{editFormError}</div>}
                      <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="sch-title">
                          Title
                        </label>
                        <Input
                          id="sch-title"
                          value={editForm.title}
                          aria-invalid={Boolean(editErrors.title)}
                          onChange={(event) => setEditField("title", event.target.value)}
                          placeholder="Masalan: Rektor stipendiyasi"
                        />
                        {editErrors.title && <p className="mt-1 text-xs text-red-600">{editErrors.title}</p>}
                      </div>

                      <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="sch-description">
                          Description
                        </label>
                        <Textarea
                          id="sch-description"
                          value={editForm.description}
                          aria-invalid={Boolean(editErrors.description)}
                          onChange={(event) => setEditField("description", event.target.value)}
                          placeholder="Scholarship haqida qisqacha ma’lumot..."
                        />
                        {editErrors.description && <p className="mt-1 text-xs text-red-600">{editErrors.description}</p>}
                      </div>

                      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                        <div>
                          <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="sch-deadline">
                            Deadline
                          </label>
                          <Input
                            id="sch-deadline"
                            type="datetime-local"
                            value={editForm.deadline}
                            aria-invalid={Boolean(editErrors.deadline)}
                            onChange={(event) => setEditField("deadline", event.target.value)}
                          />
                          {editErrors.deadline && <p className="mt-1 text-xs text-red-600">{editErrors.deadline}</p>}
                        </div>

                        <div>
                          <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="sch-ai-provider">
                            AI provider
                          </label>
                          <select
                            id="sch-ai-provider"
                            value={editForm.ai_provider}
                            aria-invalid={Boolean(editErrors.ai_provider)}
                            onChange={(event) => setEditField("ai_provider", event.target.value as AIProvider)}
                            className="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-900 shadow-sm outline-none transition focus:border-slate-400"
                          >
                            {AI_PROVIDER_OPTIONS.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                          {editErrors.ai_provider && <p className="mt-1 text-xs text-red-600">{editErrors.ai_provider}</p>}
                        </div>

                        <div>
                          <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="sch-ai-model">
                            AI model
                          </label>
                          <Input
                            id="sch-ai-model"
                            value={editForm.ai_model}
                            aria-invalid={Boolean(editErrors.ai_model)}
                            onChange={(event) => setEditField("ai_model", event.target.value)}
                            placeholder="Bo‘sh qoldirilsa provider default modeli"
                          />
                          {editErrors.ai_model && <p className="mt-1 text-xs text-red-600">{editErrors.ai_model}</p>}
                        </div>

                        <div>
                          <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="sch-winners">
                            Max winners
                          </label>
                          <Input
                            id="sch-winners"
                            type="number"
                            min={1}
                            value={editForm.max_winners}
                            aria-invalid={Boolean(editErrors.max_winners)}
                            onChange={(event) => setEditField("max_winners", Number(event.target.value) || 1)}
                          />
                          {editErrors.max_winners && <p className="mt-1 text-xs text-red-600">{editErrors.max_winners}</p>}
                        </div>
                      </div>

                      <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm">
                        <input
                          type="checkbox"
                          checked={editForm.ai_analysis_enabled}
                          onChange={(event) => setEditField("ai_analysis_enabled", event.target.checked)}
                        />
                        <div>
                          <p className="font-medium text-slate-800">Global AI analysis</p>
                          <p className="text-slate-500">Yoqqanda AI ariza tahlili umumiy oqimda ishlaydi.</p>
                        </div>
                      </label>

                      <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm">
                        <input
                          type="checkbox"
                          checked={editForm.blind_review_enabled}
                          onChange={(event) => setEditField("blind_review_enabled", event.target.checked)}
                        />
                        <div>
                          <p className="font-medium text-slate-800">Blind review</p>
                          <p className="text-slate-500">Yoqilganda jury talaba va ilmiy rahbar ma’lumotlarini ko‘rmaydi.</p>
                        </div>
                      </label>
                    </div>

                    <Card className="border-slate-200 bg-slate-50">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-base">
                          <Settings2 className="h-4 w-4 text-slate-700" />
                          Metadata
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3 text-sm text-slate-600">
                        <div className="flex items-center justify-between">
                          <span>ID</span>
                          <span className="max-w-[170px] truncate font-mono text-xs">{selectedScholarship.id}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span>Created</span>
                          <span>{formatDate(selectedScholarship.created_at)}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span>Updated</span>
                          <span>{formatDate(selectedScholarship.updated_at)}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span>Nizom</span>
                          <span>{selectedScholarship.nizom_file_url ? "Uploaded" : "Missing"}</span>
                        </div>
                        <div className="flex items-center justify-between gap-4">
                          <span>AI provider</span>
                          <span>{AI_PROVIDER_OPTIONS.find((item) => item.value === selectedScholarship.ai_provider)?.label ?? selectedScholarship.ai_provider}</span>
                        </div>
                        <div className="flex items-center justify-between gap-4">
                          <span>AI model</span>
                          <span className="max-w-[170px] truncate">{selectedScholarship.ai_model || "Provider default"}</span>
                        </div>
                        <Button
                          type="button"
                          className="w-full"
                          onClick={() => updateScholarshipMutation.mutate()}
                          disabled={updateScholarshipMutation.isPending || !editForm.title.trim()}
                        >
                          {updateScholarshipMutation.isPending ? "Saqlanmoqda..." : "Ma'lumotlarni saqlash"}
                        </Button>
                      </CardContent>
                    </Card>
                  </div>
                </TabsContent>

                <TabsContent value="workflow" className="pt-6">
                  <div className="grid gap-6 xl:grid-cols-[380px_minmax(0,1fr)]">
                    <Card className="border-slate-200">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-base">
                          <Workflow className="h-4 w-4 text-sky-600" />
                          Yangi bosqich
                        </CardTitle>
                        <CardDescription>
                          Document upload, review, exam, interview, final decision yoki appeal bosqichlarini kiriting.
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        {stageFormError && <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{stageFormError}</div>}
                        <div>
                          <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="stage-name">
                            Bosqich nomi
                          </label>
                          <Input
                            id="stage-name"
                            value={stageForm.name}
                            aria-invalid={Boolean(stageErrors.name)}
                            onChange={(event) => setStageField("name", event.target.value)}
                            placeholder="Masalan: Hujjatlarni qabul qilish"
                          />
                          {stageErrors.name && <p className="mt-1 text-xs text-red-600">{stageErrors.name}</p>}
                        </div>

                        <div>
                          <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="stage-type">
                            Stage type
                          </label>
                          <select
                            id="stage-type"
                            className={cn(
                              "h-8 w-full rounded-lg border border-slate-300 px-2.5 text-sm",
                              stageErrors.stage_type && "border-red-500",
                            )}
                            value={stageForm.stage_type}
                            onChange={(event) => setStageField("stage_type", event.target.value as ScholarshipStageType)}
                          >
                            {STAGE_TYPE_OPTIONS.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                          {stageErrors.stage_type && <p className="mt-1 text-xs text-red-600">{stageErrors.stage_type}</p>}
                        </div>

                        <div className="grid gap-3 md:grid-cols-2">
                          <div>
                            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="stage-start">
                              Start
                            </label>
                            <Input
                              id="stage-start"
                              type="datetime-local"
                              value={stageForm.starts_at}
                              aria-invalid={Boolean(stageErrors.starts_at)}
                              onChange={(event) => setStageField("starts_at", event.target.value)}
                            />
                            {stageErrors.starts_at && <p className="mt-1 text-xs text-red-600">{stageErrors.starts_at}</p>}
                          </div>

                          <div>
                            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="stage-end">
                              End
                            </label>
                            <Input
                              id="stage-end"
                              type="datetime-local"
                              value={stageForm.ends_at}
                              aria-invalid={Boolean(stageErrors.ends_at)}
                              onChange={(event) => setStageField("ends_at", event.target.value)}
                            />
                            {stageErrors.ends_at && <p className="mt-1 text-xs text-red-600">{stageErrors.ends_at}</p>}
                          </div>
                        </div>

                        <div>
                          <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="stage-description">
                            Tavsif
                          </label>
                          <Textarea
                            id="stage-description"
                            value={stageForm.description}
                            aria-invalid={Boolean(stageErrors.description)}
                            onChange={(event) => setStageField("description", event.target.value)}
                            placeholder="Bosqich vazifalari va izohlar..."
                          />
                          {stageErrors.description && <p className="mt-1 text-xs text-red-600">{stageErrors.description}</p>}
                        </div>

                        <div className="grid gap-3 md:grid-cols-2">
                          <label className="flex items-center gap-2 rounded-xl border border-slate-200 p-3 text-sm">
                            <input
                              type="checkbox"
                              checked={stageForm.is_required}
                              onChange={(event) => setStageField("is_required", event.target.checked)}
                            />
                            Required
                          </label>

                          <label className="flex items-center gap-2 rounded-xl border border-slate-200 p-3 text-sm">
                            <input
                              type="checkbox"
                              checked={stageForm.is_active}
                              onChange={(event) => setStageField("is_active", event.target.checked)}
                            />
                            Active
                          </label>
                        </div>

                        <Button
                          type="button"
                          className="w-full"
                          onClick={() => createStageMutation.mutate()}
                          disabled={
                            createStageMutation.isPending ||
                            !stageForm.name.trim() ||
                            !stageForm.starts_at ||
                            !stageForm.ends_at
                          }
                        >
                          {createStageMutation.isPending ? "Qo‘shilmoqda..." : "Bosqich qo‘shish"}
                        </Button>
                      </CardContent>
                    </Card>

                    <Card className="border-slate-200">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-base">
                          <CalendarRange className="h-4 w-4 text-amber-600" />
                          Workflow timeline
                        </CardTitle>
                        <CardDescription>
                          Scholarship turiga qarab bosqichlar ixtiyoriy va tartibli bo‘ladi.
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        {(stagesQuery.data ?? []).map((stage) => (
                          <div key={stage.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                              <div>
                                <div className="flex flex-wrap items-center gap-2">
                                  <Badge variant="outline">{`#${stage.order_index + 1}`}</Badge>
                                  <p className="font-semibold text-slate-900">{stage.name}</p>
                                  <Badge variant={stage.is_active ? "secondary" : "outline"}>
                                    {stage.is_active ? "active" : "inactive"}
                                  </Badge>
                                  <Badge variant="outline">{stageTypeLabel(stage.stage_type)}</Badge>
                                </div>
                                <p className="mt-2 text-sm text-slate-600">{stage.description || "Tavsif kiritilmagan."}</p>
                                <p className="mt-2 text-xs text-slate-500">
                                  {formatDate(stage.starts_at)} - {formatDate(stage.ends_at)}
                                </p>
                              </div>

                              <div className="flex items-center gap-2">
                                <Badge variant={stage.is_required ? "default" : "outline"}>
                                  {stage.is_required ? "required" : "optional"}
                                </Badge>
                                <Button
                                  type="button"
                                  variant="destructive"
                                  size="sm"
                                  onClick={() => deleteStageMutation.mutate(stage.id)}
                                  disabled={deleteStageMutation.isPending}
                                >
                                  O‘chirish
                                </Button>
                              </div>
                            </div>
                          </div>
                        ))}

                        {(stagesQuery.data ?? []).length === 0 && (
                          <EmptyState
                            title="Workflow bosqichlari hali yo‘q"
                            description="Kamida application, review va final decision bosqichlarini belgilash tavsiya qilinadi."
                          />
                        )}
                      </CardContent>
                    </Card>
                  </div>
                </TabsContent>

                <TabsContent value="columns" className="pt-6">
                  <ColumnBuilder
                    scholarshipId={selectedScholarshipId}
                    columns={selectedScholarship.columns}
                    importedColumns={importedColumns}
                    form={columnForm}
                    errors={columnErrors}
                    formError={columnFormError}
                    onImportedColumnsChange={setImportedColumns}
                    onFieldChange={setColumnField}
                    onImportColumns={() => importColumnsMutation.mutate()}
                    onCreateColumn={() => createColumnMutation.mutate()}
                    onDeleteColumn={(columnId) => deleteColumnMutation.mutate(columnId)}
                    onReorderColumns={(order) => reorderColumnsMutation.mutate(order)}
                    isImportPending={importColumnsMutation.isPending}
                    isCreatePending={createColumnMutation.isPending}
                    isDeletePending={deleteColumnMutation.isPending}
                    isReorderPending={reorderColumnsMutation.isPending}
                  />
                </TabsContent>

                <TabsContent value="jury" className="pt-6">
                  <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
                    <Card className="border-slate-200">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-base">
                          <Users className="h-4 w-4 text-emerald-600" />
                          Hakam biriktirish
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <select
                          className={cn(
                            "h-8 w-full rounded-lg border border-slate-300 px-2.5 text-sm",
                            juryError && "border-red-500",
                          )}
                          value={selectedJuryId}
                          onChange={(event) => {
                            setSelectedJuryId(event.target.value)
                            setJuryError(null)
                          }}
                        >
                          <option value="">Hakam tanlang...</option>
                          {availableJuryUsers.map((user) => (
                            <option key={user.id} value={user.id}>
                              {user.full_name} ({user.email})
                            </option>
                          ))}
                        </select>
                        {juryError && <p className="text-xs text-red-600">{juryError}</p>}

                        <Button
                          type="button"
                          className="w-full"
                          onClick={() => assignJuryMutation.mutate()}
                          disabled={assignJuryMutation.isPending || !selectedJuryId}
                        >
                          {assignJuryMutation.isPending ? "Biriktirilmoqda..." : "Hakam biriktirish"}
                        </Button>
                      </CardContent>
                    </Card>

                    <Card className="border-slate-200">
                      <CardHeader>
                        <CardTitle>Assigned jury</CardTitle>
                        <CardDescription>Faqat biriktirilgan hakamlar arizalarni baholaydi.</CardDescription>
                      </CardHeader>
                      <CardContent className="grid gap-3">
                        {(juryQuery.data ?? []).map((jury) => (
                          <div key={jury.id} className="flex items-center justify-between rounded-2xl border border-slate-200 p-4">
                            <div>
                              <p className="font-medium text-slate-900">{jury.full_name}</p>
                              <p className="text-sm text-slate-500">{jury.email}</p>
                            </div>
                            <Button
                              type="button"
                              variant="destructive"
                              size="sm"
                              onClick={() => removeJuryMutation.mutate(jury.id)}
                              disabled={removeJuryMutation.isPending}
                            >
                              Olib tashlash
                            </Button>
                          </div>
                        ))}

                        {(juryQuery.data ?? []).length === 0 && (
                          <EmptyState
                            title="Hakamlar hali biriktirilmagan"
                            description="Baholash boshlanishidan oldin kamida bitta jury a’zosini scholarshipga biriktiring."
                          />
                        )}
                      </CardContent>
                    </Card>
                  </div>
                </TabsContent>

                <TabsContent value="applications" className="pt-6">
                  <div className="space-y-4">
                    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                      <div>
                        <h3 className="text-base font-semibold text-slate-900">Arizalar va natijalar</h3>
                        <p className="text-sm text-slate-500">
                          Umumiy ro‘yxat. Batafsil application audit va ranking uchun alohida sahifalar ishlatiladi.
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Link href={`/admin/applications?scholarshipId=${selectedScholarshipId}`}>
                          <Button type="button" variant="outline">
                            Applications sahifasiga o‘tish
                          </Button>
                        </Link>
                        <Link href="/admin/results">
                          <Button type="button" variant="outline">
                            Ranking sahifasiga o‘tish
                          </Button>
                        </Link>
                      </div>
                    </div>

                    <Card className="border-slate-200">
                      <CardContent className="pt-6">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Student</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Score</TableHead>
                            <TableHead>Submitted</TableHead>
                            <TableHead className="text-right">Action</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(applicationsQuery.data ?? []).map((application) => (
                            <TableRow key={application.id}>
                                <TableCell>
                                  <div>
                                    <p className="font-medium text-slate-900">{application.student?.full_name ?? "-"}</p>
                                    <p className="text-xs text-slate-500">{application.student?.email ?? application.id}</p>
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <Badge variant="outline">{applicationStatusLabel(application.status)}</Badge>
                                </TableCell>
                                <TableCell>
                                  {typeof application.total_score === "number" ? application.total_score.toFixed(2) : "-"}
                                </TableCell>
                                <TableCell>{formatDate(application.submitted_at)}</TableCell>
                                <TableCell className="text-right">
                                  <Link
                                    href={`/admin/applications/${application.id}`}
                                    className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                                  >
                                    Ochish
                                  </Link>
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>

                        {(applicationsQuery.data ?? []).length === 0 && (
                          <EmptyState
                            title="Arizalar hali yo‘q"
                            description="Studentlar stipendiyaga topshirgan arizalar shu bo‘limda paydo bo‘ladi."
                          />
                        )}
                      </CardContent>
                    </Card>
                  </div>
                </TabsContent>

                <TabsContent value="status" className="pt-6">
                  <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
                    <Card className="border-slate-200">
                      <CardHeader>
                        <CardTitle>Current state</CardTitle>
                        <CardDescription>Scholarship oqimini shu yerdan boshqaring.</CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="rounded-2xl bg-slate-900 p-5 text-white">
                          <p className="text-xs uppercase tracking-[0.2em] text-slate-300">Status</p>
                          <div className="mt-3">
                            <StatusBadge status={selectedScholarship.status} className="border-white/20 bg-white/10 text-white" />
                          </div>
                          <p className="mt-2 text-sm text-slate-300">
                            Winner announcement uchun odatda `final_decision` stage faol bo‘lishi kerak.
                          </p>
                        </div>
                      </CardContent>
                    </Card>

                    <div className="grid gap-4 md:grid-cols-2">
                      {STATUS_OPTIONS.map((option) => (
                        <Card key={option.value} className="border-slate-200">
                          <CardHeader>
                            <div className="flex items-center justify-between gap-3">
                              <CardTitle className="text-base">{option.label}</CardTitle>
                              <StatusBadge status={option.value} />
                            </div>
                            <CardDescription>{option.hint}</CardDescription>
                          </CardHeader>
                          <CardContent>
                            <Button
                              type="button"
                              variant={selectedScholarship.status === option.value ? "secondary" : "outline"}
                              onClick={() => setPendingStatus(option.value)}
                              disabled={changeStatusMutation.isPending || selectedScholarship.status === option.value}
                            >
                              {selectedScholarship.status === option.value ? "Faol holat" : `${option.label} ga o‘tkazish`}
                            </Button>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        )}
      </div>

      <Dialog
        open={Boolean(pendingStatus)}
        onOpenChange={(open) => {
          if (!open) {
            setPendingStatus(null)
          }
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Statusni o‘zgartirish</DialogTitle>
            <DialogDescription>
              {pendingStatus ? `${STATUS_OPTIONS.find((item) => item.value === pendingStatus)?.label} holatiga o‘tkazishdan oldin tekshirib chiqing.` : ""}
            </DialogDescription>
          </DialogHeader>

          {pendingStatus && (
            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-slate-900">{selectedScholarship?.title}</p>
                    <p className="text-xs text-slate-500">Joriy holat: {selectedScholarship?.status}</p>
                  </div>
                  <StatusBadge status={pendingStatus} />
                </div>
              </div>

              {pendingStatusValidation.errors.length > 0 && (
                <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                  <p className="font-medium">Bloklovchi tekshiruvlar</p>
                  <ul className="mt-2 list-disc space-y-1 pl-5">
                    {pendingStatusValidation.errors.map((message) => (
                      <li key={message}>{message}</li>
                    ))}
                  </ul>
                </div>
              )}

              {pendingStatusValidation.warnings.length > 0 && (
                <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                  <p className="font-medium">Ogohlantirishlar</p>
                  <ul className="mt-2 list-disc space-y-1 pl-5">
                    {pendingStatusValidation.warnings.map((message) => (
                      <li key={message}>{message}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setPendingStatus(null)}>
              Bekor qilish
            </Button>
            <Button
              type="button"
              onClick={() => {
                if (pendingStatus) {
                  changeStatusMutation.mutate(pendingStatus, {
                    onSuccess: () => setPendingStatus(null),
                  })
                }
              }}
              disabled={changeStatusMutation.isPending || pendingStatusValidation.errors.length > 0}
            >
              {changeStatusMutation.isPending ? "Saqlanmoqda..." : "Tasdiqlash"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={createOpen}
        onOpenChange={(open) => {
          setCreateOpen(open)
          if (!open) {
            setCreateErrors({})
            setCreateFormError(null)
          }
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Yangi scholarship yaratish</DialogTitle>
            <DialogDescription>Asosiy ma’lumotlarni kiriting. Qolgan sozlamalarni keyin tablar orqali to‘ldirasiz.</DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            {createFormError && <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{createFormError}</div>}
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="create-title">
                Title
              </label>
              <Input
                id="create-title"
                value={createForm.title}
                aria-invalid={Boolean(createErrors.title)}
                onChange={(event) => setCreateField("title", event.target.value)}
                placeholder="Masalan: Prezident stipendiyasi"
              />
              {createErrors.title && <p className="mt-1 text-xs text-red-600">{createErrors.title}</p>}
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="create-description">
                Description
              </label>
              <Textarea
                id="create-description"
                value={createForm.description}
                aria-invalid={Boolean(createErrors.description)}
                onChange={(event) => setCreateField("description", event.target.value)}
                placeholder="Qisqacha tavsif..."
              />
              {createErrors.description && <p className="mt-1 text-xs text-red-600">{createErrors.description}</p>}
            </div>

            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="create-deadline">
                  Deadline
                </label>
                <Input
                  id="create-deadline"
                  type="datetime-local"
                  value={createForm.deadline}
                  aria-invalid={Boolean(createErrors.deadline)}
                  onChange={(event) => setCreateField("deadline", event.target.value)}
                />
                {createErrors.deadline && <p className="mt-1 text-xs text-red-600">{createErrors.deadline}</p>}
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="create-ai-provider">
                  AI provider
                </label>
                <select
                  id="create-ai-provider"
                  value={createForm.ai_provider}
                  aria-invalid={Boolean(createErrors.ai_provider)}
                  onChange={(event) => setCreateField("ai_provider", event.target.value as AIProvider)}
                  className="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-900 shadow-sm outline-none transition focus:border-slate-400"
                >
                  {AI_PROVIDER_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                {createErrors.ai_provider && <p className="mt-1 text-xs text-red-600">{createErrors.ai_provider}</p>}
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="create-ai-model">
                  AI model
                </label>
                <Input
                  id="create-ai-model"
                  value={createForm.ai_model}
                  aria-invalid={Boolean(createErrors.ai_model)}
                  onChange={(event) => setCreateField("ai_model", event.target.value)}
                  placeholder="Bo‘sh qoldirilsa provider default modeli"
                />
                {createErrors.ai_model && <p className="mt-1 text-xs text-red-600">{createErrors.ai_model}</p>}
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="create-max-winners">
                  Max winners
                </label>
                <Input
                  id="create-max-winners"
                  type="number"
                  min={1}
                  value={createForm.max_winners}
                  aria-invalid={Boolean(createErrors.max_winners)}
                  onChange={(event) => setCreateField("max_winners", Number(event.target.value) || 1)}
                />
                {createErrors.max_winners && <p className="mt-1 text-xs text-red-600">{createErrors.max_winners}</p>}
              </div>
            </div>

            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 p-4 text-sm">
              <input
                type="checkbox"
                checked={createForm.ai_analysis_enabled}
                onChange={(event) => setCreateField("ai_analysis_enabled", event.target.checked)}
              />
              AI analysis enabled
            </label>

            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 p-4 text-sm">
              <input
                type="checkbox"
                checked={createForm.blind_review_enabled}
                onChange={(event) => setCreateField("blind_review_enabled", event.target.checked)}
              />
              Blind review enabled
            </label>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>
              Bekor qilish
            </Button>
            <Button
              type="button"
              onClick={() => createScholarshipMutation.mutate()}
              disabled={createScholarshipMutation.isPending || !createForm.title.trim()}
            >
              {createScholarshipMutation.isPending ? "Yaratilmoqda..." : "Yaratish"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={createFromTemplateOpen}
        onOpenChange={(open) => {
          setCreateFromTemplateOpen(open)
          if (!open) {
            setTemplateInstantiateErrors({})
            setTemplateInstantiateFormError(null)
          }
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Template asosida scholarship yaratish</DialogTitle>
            <DialogDescription>
              Tayyor columns va workflow bosqichlarini qayta ishlatish uchun templatedan yangi scholarship oching.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            {templateInstantiateFormError && (
              <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{templateInstantiateFormError}</div>
            )}

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="template-id">
                Template
              </label>
              <select
                id="template-id"
                className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"
                value={templateInstantiateForm.template_id}
                onChange={(event) => {
                  const templateId = event.target.value
                  const template = (templatesQuery.data ?? []).find((item) => item.id === templateId) ?? null
                  setTemplateInstantiateForm({
                    template_id: templateId,
                    title: template?.snapshot_title ?? "",
                    description: template?.description ?? "",
                    deadline: "",
                    starts_at: toDateTimeLocal(new Date().toISOString()),
                  })
                  setTemplateInstantiateErrors({})
                  setTemplateInstantiateFormError(null)
                }}
              >
                <option value="">Template tanlang</option>
                {(templatesQuery.data ?? []).map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name}
                  </option>
                ))}
              </select>
              {templateInstantiateErrors.template_id && (
                <p className="mt-1 text-xs text-red-600">{templateInstantiateErrors.template_id}</p>
              )}
            </div>

            {selectedTemplate && (
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                <p className="font-medium text-slate-900">{selectedTemplate.name}</p>
                <p className="mt-1 text-slate-600">
                  Columns: {selectedTemplate.column_count} · Stages: {selectedTemplate.stage_count} · Tasks:{" "}
                  {selectedTemplate.task_count}
                </p>
                <p className="mt-1 text-slate-600">
                  AI: {selectedTemplate.ai_analysis_enabled ? "On" : "Off"} · Blind review:{" "}
                  {selectedTemplate.blind_review_enabled ? "On" : "Off"} · Max winners: {selectedTemplate.max_winners}
                </p>
                <p className="mt-1 text-slate-600">
                  LLM: {formatAiConfig(selectedTemplate.ai_provider, selectedTemplate.ai_model)}
                </p>
              </div>
            )}

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="template-title">
                Yangi scholarship title
              </label>
              <Input
                id="template-title"
                value={templateInstantiateForm.title}
                aria-invalid={Boolean(templateInstantiateErrors.title)}
                onChange={(event) => setTemplateInstantiateField("title", event.target.value)}
                placeholder="Masalan: Rektor stipendiyasi 2026"
              />
              {templateInstantiateErrors.title && (
                <p className="mt-1 text-xs text-red-600">{templateInstantiateErrors.title}</p>
              )}
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="template-description">
                Description
              </label>
              <Textarea
                id="template-description"
                value={templateInstantiateForm.description}
                aria-invalid={Boolean(templateInstantiateErrors.description)}
                onChange={(event) => setTemplateInstantiateField("description", event.target.value)}
                placeholder="Template description yoki yangi izoh..."
              />
              {templateInstantiateErrors.description && (
                <p className="mt-1 text-xs text-red-600">{templateInstantiateErrors.description}</p>
              )}
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="template-deadline">
                  Deadline
                </label>
                <Input
                  id="template-deadline"
                  type="datetime-local"
                  value={templateInstantiateForm.deadline}
                  aria-invalid={Boolean(templateInstantiateErrors.deadline)}
                  onChange={(event) => setTemplateInstantiateField("deadline", event.target.value)}
                />
                {templateInstantiateErrors.deadline && (
                  <p className="mt-1 text-xs text-red-600">{templateInstantiateErrors.deadline}</p>
                )}
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="template-starts-at">
                  Workflow base start
                </label>
                <Input
                  id="template-starts-at"
                  type="datetime-local"
                  value={templateInstantiateForm.starts_at}
                  aria-invalid={Boolean(templateInstantiateErrors.starts_at)}
                  onChange={(event) => setTemplateInstantiateField("starts_at", event.target.value)}
                />
                {templateInstantiateErrors.starts_at && (
                  <p className="mt-1 text-xs text-red-600">{templateInstantiateErrors.starts_at}</p>
                )}
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setCreateFromTemplateOpen(false)}>
              Bekor qilish
            </Button>
            <Button type="button" onClick={() => instantiateTemplateMutation.mutate()} disabled={instantiateTemplateMutation.isPending}>
              {instantiateTemplateMutation.isPending ? "Yaratilmoqda..." : "Template asosida yaratish"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={saveTemplateOpen}
        onOpenChange={(open) => {
          setSaveTemplateOpen(open)
          if (!open) {
            setTemplateErrors({})
            setTemplateFormError(null)
          }
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Scholarshipni template sifatida saqlash</DialogTitle>
            <DialogDescription>
              Columns, workflow stage va stage tasklar snapshot qilinadi. Jury assignment va arizalar ko‘chirilmaydi.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            {templateFormError && <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{templateFormError}</div>}

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="save-template-name">
                Template nomi
              </label>
              <Input
                id="save-template-name"
                value={templateForm.name}
                aria-invalid={Boolean(templateErrors.name)}
                onChange={(event) => setTemplateField("name", event.target.value)}
                placeholder="Masalan: Rektor base template"
              />
              {templateErrors.name && <p className="mt-1 text-xs text-red-600">{templateErrors.name}</p>}
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="save-template-description">
                Description
              </label>
              <Textarea
                id="save-template-description"
                value={templateForm.description}
                aria-invalid={Boolean(templateErrors.description)}
                onChange={(event) => setTemplateField("description", event.target.value)}
                placeholder="Qachon ishlatilishi yoki template izohi..."
              />
              {templateErrors.description && <p className="mt-1 text-xs text-red-600">{templateErrors.description}</p>}
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setSaveTemplateOpen(false)}>
              Bekor qilish
            </Button>
            <Button type="button" onClick={() => saveTemplateMutation.mutate()} disabled={saveTemplateMutation.isPending}>
              {saveTemplateMutation.isPending ? "Saqlanmoqda..." : "Template saqlash"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
