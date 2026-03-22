from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import LLMProvider
from app.services.file_service import build_file_download_url


class ScholarshipTemplateCreate(BaseModel):
    scholarship_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class ScholarshipTemplateInstantiate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    deadline: datetime | None = None
    starts_at: datetime | None = None


class ScholarshipTemplateOut(BaseModel):
    id: uuid.UUID
    created_by: uuid.UUID
    source_scholarship_id: uuid.UUID | None
    name: str
    description: str | None
    snapshot_title: str | None
    ai_analysis_enabled: bool
    blind_review_enabled: bool
    max_winners: int
    ai_provider: LLMProvider
    ai_model: str | None
    column_count: int
    stage_count: int
    task_count: int
    nizom_file_url: str | None
    created_at: datetime
    updated_at: datetime

    @field_validator("nizom_file_url", mode="before")
    @classmethod
    def _presign_nizom_file_url(cls, value: str | None) -> str | None:
        return build_file_download_url(value)
