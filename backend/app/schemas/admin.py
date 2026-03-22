from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ApplicationStatus, ScholarshipStatus


class TrendPoint(BaseModel):
    date: str
    count: int


class RecentActivityItem(BaseModel):
    entity_type: str
    entity_id: str
    title: str
    subtitle: str | None = None
    status: str | None = None
    created_at: datetime


class AdminStatsOut(BaseModel):
    total_scholarships: int
    scholarships_by_status: dict[str, int]
    total_applications: int
    applications_by_status: dict[str, int]
    total_users: int
    users_by_role: dict[str, int]
    total_ai_jobs: int
    ai_jobs_by_status: dict[str, int]
    ai_jobs_by_type: dict[str, int]
    application_trend: list[TrendPoint]
    recent_activity: list[RecentActivityItem]


class EvaluationConsistencySummary(BaseModel):
    jury_count: int
    average_score: float | None
    min_score: float | None
    max_score: float | None
    score_spread: float | None
    score_stddev: float | None
    warning_threshold: float
    is_flagged: bool


class EvaluationConsistencyItem(BaseModel):
    evaluation_id: uuid.UUID
    jury_id: uuid.UUID
    jury_name: str
    total_score: float | None
    final_comment: str | None
    submitted_at: datetime | None


class ScholarshipResultRow(BaseModel):
    rank: int | None
    application_id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    status: ApplicationStatus
    total_score: float | None
    is_winner: bool
    submitted_at: datetime | None
    consistency: EvaluationConsistencySummary | None = None


class ScholarshipResultsOut(BaseModel):
    scholarship_id: uuid.UUID
    scholarship_title: str
    scholarship_status: ScholarshipStatus
    max_winners: int
    winners_count: int
    rows: list[ScholarshipResultRow]


class ApplicationConsistencyOut(BaseModel):
    application_id: uuid.UUID
    scholarship_id: uuid.UUID
    student_id: uuid.UUID
    application_status: ApplicationStatus
    summary: EvaluationConsistencySummary
    evaluations: list[EvaluationConsistencyItem]
