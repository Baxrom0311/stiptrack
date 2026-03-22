from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AppealStatus, ScholarshipStageType, StageTaskStatus, UserRole
from app.services.file_service import build_file_download_url


class StageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    stage_type: ScholarshipStageType
    description: str | None = None
    starts_at: datetime
    ends_at: datetime
    is_required: bool = True
    is_active: bool = True
    config: dict | None = None


class StageUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    stage_type: ScholarshipStageType | None = None
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_required: bool | None = None
    is_active: bool | None = None
    config: dict | None = None


class StageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scholarship_id: uuid.UUID
    name: str
    stage_type: ScholarshipStageType
    description: str | None
    order_index: int
    starts_at: datetime
    ends_at: datetime
    is_required: bool
    is_active: bool
    config: dict | None
    created_at: datetime
    updated_at: datetime


class StageReorder(BaseModel):
    order: list[uuid.UUID]


class StageTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    assigned_to: uuid.UUID | None = None
    assigned_role: UserRole | None = None
    due_at: datetime | None = None


class StageTaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    assigned_to: uuid.UUID | None = None
    assigned_role: UserRole | None = None
    status: StageTaskStatus | None = None
    due_at: datetime | None = None


class StageTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stage_id: uuid.UUID
    title: str
    description: str | None
    assigned_to: uuid.UUID | None
    assigned_role: UserRole | None
    status: StageTaskStatus
    due_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AppealCreate(BaseModel):
    reason: str = Field(min_length=10, max_length=5000)
    attachment_url: str | None = None


class AppealDecision(BaseModel):
    status: AppealStatus
    response_text: str = Field(min_length=5, max_length=5000)
    score_after: float | None = Field(default=None, ge=0)


class AppealOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scholarship_id: uuid.UUID
    application_id: uuid.UUID
    student_id: uuid.UUID
    status: AppealStatus
    reason: str
    response_text: str | None
    attachment_url: str | None
    filed_at: datetime
    resolved_at: datetime | None
    resolved_by: uuid.UUID | None
    score_before: float | None
    score_after: float | None
    created_at: datetime
    updated_at: datetime

    @field_validator("attachment_url", mode="before")
    @classmethod
    def _presign_attachment_url(cls, value: str | None) -> str | None:
        return build_file_download_url(value)
