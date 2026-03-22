export type Role = "admin" | "jury" | "student"
export type AIProvider = "claude" | "openai" | "gemini" | "ollama" | "deepseek"

export interface User {
  id: string
  full_name: string
  email: string
  role: Role
  department?: string | null
  student_id?: string | null
  is_supervisor: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
  access_expires_in: number
  refresh_expires_in: number
}

export type ScholarshipStatus = "draft" | "open" | "closed" | "done"

export type FieldType = "text" | "textarea" | "file" | "number" | "date" | "select" | "url"

export interface Column {
  id: string
  scholarship_id: string
  name: string
  description?: string | null
  field_type: FieldType
  select_options?: string[] | null
  is_required: boolean
  ai_analyze: boolean
  max_score: number
  input_min?: number | null
  input_max?: number | null
  order_index: number
}

export interface Scholarship {
  id: string
  created_by: string
  title: string
  description?: string | null
  nizom_file_url?: string | null
  status: ScholarshipStatus
  deadline?: string | null
  ai_analysis_enabled: boolean
  blind_review_enabled: boolean
  max_winners: number
  ai_provider: AIProvider
  ai_model?: string | null
  created_at?: string
  updated_at?: string
  columns?: Column[]
}

export interface ScholarshipDetail extends Scholarship {
  created_at: string
  updated_at: string
  columns: Column[]
}

export interface ScholarshipInput {
  title: string
  description?: string | null
  deadline?: string | null
  ai_analysis_enabled: boolean
  blind_review_enabled: boolean
  max_winners: number
  ai_provider: AIProvider
  ai_model?: string | null
}

export interface ColumnInput {
  name: string
  description?: string | null
  field_type: FieldType
  select_options?: string[] | null
  is_required: boolean
  ai_analyze: boolean
  max_score: number
  input_min?: number | null
  input_max?: number | null
}

export interface JuryMember {
  id: string
  full_name: string
  email: string
}

export interface ScholarshipTemplate {
  id: string
  created_by: string
  source_scholarship_id?: string | null
  name: string
  description?: string | null
  snapshot_title?: string | null
  ai_analysis_enabled: boolean
  blind_review_enabled: boolean
  max_winners: number
  ai_provider: AIProvider
  ai_model?: string | null
  column_count: number
  stage_count: number
  task_count: number
  nizom_file_url?: string | null
  created_at: string
  updated_at: string
}

export interface ScholarshipTemplateCreateInput {
  scholarship_id: string
  name: string
  description?: string | null
}

export interface ScholarshipTemplateInstantiateInput {
  title: string
  description?: string | null
  deadline?: string | null
  starts_at?: string | null
}

export type ApplicationStatus = "draft" | "submitted" | "in_review" | "winner" | "rejected"

export interface Application {
  id: string
  scholarship_id: string
  student_id: string
  supervisor_id?: string | null
  status: ApplicationStatus
  submitted_at?: string | null
  ai_summary?: string | null
  total_score?: number | null
  created_at?: string
  updated_at?: string
}

export interface ApplicationListItem extends Application {
  scholarship?: Scholarship | null
  student?: User | null
}

export interface ApplicationValueDetail {
  id: string
  column_id: string
  value_text?: string | null
  value_file_url?: string | null
  ai_analysis?: string | null
  ai_score?: number | null
  plagiarism_score?: number | null
  plagiarism_matches?: ApplicationValuePlagiarismMatch[] | null
  plagiarism_checked_at?: string | null
  column?: Column | null
}

export interface ApplicationValuePlagiarismMatch {
  application_id?: string | null
  application_status: ApplicationStatus | string
  similarity_percent: number
  matched_text_excerpt: string
}

export interface ApplicationDetailResponse extends Application {
  scholarship?: Scholarship | null
  student?: User | null
  supervisor?: User | null
  values: ApplicationValueDetail[]
}

export interface ApplicationStatusLogEntry {
  id: string
  application_id: string
  scholarship_id: string
  previous_status?: ApplicationStatus | null
  new_status: ApplicationStatus
  changed_by?: string | null
  source: string
  note?: string | null
  created_at: string
  changed_by_user?: User | null
}

export interface Evaluation {
  id: string | null
  application_id: string
  jury_id: string
  scores: Record<string, number>
  total_score?: number | null
  final_comment?: string | null
  ai_generated: boolean
  is_submitted: boolean
  submitted_at?: string | null
}

export interface Achievement {
  id: string
  student_id: string
  title: string
  type?: "paper" | "award" | "project" | "cert" | "olympiad" | "other"
  file_url?: string | null
  date?: string | null
  description?: string | null
  created_at?: string
}

export type AIJobType = "column_gen" | "app_analysis" | "review_gen"
export type AIJobLifecycleStatus = "pending" | "running" | "done" | "failed"

export type ScholarshipStageType = "application" | "review" | "exam" | "interview" | "final_decision" | "appeal"
export type StageTaskStatus = "todo" | "in_progress" | "done" | "canceled"

export interface AIJob {
  id: string
  job_type: AIJobType
  ref_id: string
  model_used?: string | null
  status: AIJobLifecycleStatus
  result?: Record<string, unknown> | null
  error_msg?: string | null
  created_at: string
  finished_at?: string | null
}

export interface CriterionSubScore {
  label: string
  score: number
}

export interface CriterionDetailed {
  name: string
  max_score: number
  description: string
  sub_scores: CriterionSubScore[]
}

export interface NizomParseResponse {
  title?: string | null
  purpose: string
  requirements: string[]
  evaluation_criteria: string[]
  evaluation_criteria_detailed: CriterionDetailed[]
  additional_docs: string[]
  scoring_type: "table" | "text" | "mixed" | string
  total_max_score: number
  eligible_students?: string | null
  selection_stages?: string | null
  deadline_hint?: string | null
  amount_hint?: string | null
}

export interface SuggestedColumn {
  name: string
  criterion_ref: string
  description: string
  field_type: FieldType
  select_options?: string[] | null
  is_required: boolean
  ai_analyze: boolean
  max_score: number
  input_min?: number | null
  input_max?: number | null
  order_index: number
  validation_hint?: string | null
}

export interface SuggestColumnsResult {
  columns: SuggestedColumn[]
  total_max_score: number
  ai_columns_count: number
  reasoning: string
}

export interface AIReviewResponse {
  review_text: string
  summary: string
  recommendation_note: string
  total_score: number
  max_total_score: number
  score_percent: number
}

export interface AdminTrendPoint {
  date: string
  count: number
}

export interface AdminRecentActivityItem {
  entity_type: string
  entity_id: string
  title: string
  subtitle?: string | null
  status?: string | null
  created_at: string
}

export interface AdminStats {
  total_scholarships: number
  scholarships_by_status: Record<string, number>
  total_applications: number
  applications_by_status: Record<string, number>
  total_users: number
  users_by_role: Record<string, number>
  total_ai_jobs: number
  ai_jobs_by_status: Record<string, number>
  ai_jobs_by_type: Record<string, number>
  application_trend: AdminTrendPoint[]
  recent_activity: AdminRecentActivityItem[]
}

export interface EvaluationConsistencySummary {
  jury_count: number
  average_score?: number | null
  min_score?: number | null
  max_score?: number | null
  score_spread?: number | null
  score_stddev?: number | null
  warning_threshold: number
  is_flagged: boolean
}

export interface EvaluationConsistencyItem {
  evaluation_id: string
  jury_id: string
  jury_name: string
  total_score?: number | null
  final_comment?: string | null
  submitted_at?: string | null
}

export interface ScholarshipResultRow {
  rank?: number | null
  application_id: string
  student_id: string
  student_name: string
  status: ApplicationStatus
  total_score?: number | null
  is_winner: boolean
  submitted_at?: string | null
  consistency?: EvaluationConsistencySummary | null
}

export interface ScholarshipResults {
  scholarship_id: string
  scholarship_title: string
  scholarship_status: ScholarshipStatus
  max_winners: number
  winners_count: number
  rows: ScholarshipResultRow[]
}

export interface ApplicationConsistency {
  application_id: string
  scholarship_id: string
  student_id: string
  application_status: ApplicationStatus
  summary: EvaluationConsistencySummary
  evaluations: EvaluationConsistencyItem[]
}

export interface AnnounceWinnersResponse {
  detail: string
  winner_ids: string[]
}

export interface WorkflowStage {
  id: string
  scholarship_id: string
  name: string
  stage_type: ScholarshipStageType
  description?: string | null
  order_index: number
  starts_at: string
  ends_at: string
  is_required: boolean
  is_active: boolean
  config?: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface WorkflowStageInput {
  name: string
  stage_type: ScholarshipStageType
  description?: string | null
  starts_at: string
  ends_at: string
  is_required: boolean
  is_active: boolean
  config?: Record<string, unknown> | null
}

export interface StageTask {
  id: string
  stage_id: string
  title: string
  description?: string | null
  assigned_to?: string | null
  assigned_role?: Role | null
  status: StageTaskStatus
  due_at?: string | null
  completed_at?: string | null
  created_at: string
  updated_at: string
}

export interface StageTaskInput {
  title: string
  description?: string | null
  assigned_to?: string | null
  assigned_role?: Role | null
  due_at?: string | null
}
