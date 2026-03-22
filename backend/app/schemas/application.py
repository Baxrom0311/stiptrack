from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ApplicationStatus
from app.schemas.scholarship import ColumnOut, ScholarshipOut
from app.schemas.user import UserOut
from app.services.file_service import build_file_download_url


class ApplicationValuePlagiarismMatchOut(BaseModel):
    application_id: uuid.UUID | None
    application_status: ApplicationStatus | str
    similarity_percent: float
    matched_text_excerpt: str


class ApplicationValueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    column_id: uuid.UUID
    value_text: str | None
    value_file_url: str | None
    ai_analysis: str | None
    ai_score: float | None
    plagiarism_score: float | None = None
    plagiarism_matches: list[ApplicationValuePlagiarismMatchOut] | None = None
    plagiarism_checked_at: datetime | None = None
    column: ColumnOut | None = None

    @field_validator("value_file_url", mode="before")
    @classmethod
    def _presign_value_file_url(cls, value: str | None) -> str | None:
        return build_file_download_url(value)


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scholarship_id: uuid.UUID
    student_id: uuid.UUID
    supervisor_id: uuid.UUID | None
    status: ApplicationStatus
    submitted_at: datetime | None
    ai_summary: str | None
    total_score: float | None
    created_at: datetime
    updated_at: datetime


class ApplicationStatusLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    scholarship_id: uuid.UUID
    previous_status: ApplicationStatus | None
    new_status: ApplicationStatus
    changed_by: uuid.UUID | None
    source: str
    note: str | None
    created_at: datetime
    changed_by_user: UserOut | None = None


class ApplicationListOut(ApplicationOut):
    scholarship: ScholarshipOut | None = None
    student: UserOut | None = None


class ApplicationDetail(ApplicationOut):
    scholarship: ScholarshipOut | None = None
    student: UserOut | None = None
    supervisor: UserOut | None = None
    values: list[ApplicationValueOut] = Field(default_factory=list)


class ApplicationValueUpdate(BaseModel):
    supervisor_id: uuid.UUID | None = None
    values: dict[str, str | None] | None = None


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


class ApplicationCreateResponse(BaseModel):
    application_id: uuid.UUID
    status: ApplicationStatus


class AnnounceWinnersResponse(BaseModel):
    detail: str
    winner_ids: list[str]
