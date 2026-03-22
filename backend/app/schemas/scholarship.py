from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ColumnFieldType, LLMProvider, ScholarshipStatus
from app.services.file_service import build_file_download_url


def _normalize_ai_model(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


class ColumnCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    field_type: ColumnFieldType = ColumnFieldType.TEXT
    select_options: list[str] | None = None
    is_required: bool = True
    ai_analyze: bool = False
    max_score: int = Field(default=10, ge=0, le=100)
    input_min: int | None = None
    input_max: int | None = None


class ColumnUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    field_type: ColumnFieldType | None = None
    select_options: list[str] | None = None
    is_required: bool | None = None
    ai_analyze: bool | None = None
    max_score: int | None = Field(default=None, ge=0, le=100)
    input_min: int | None = None
    input_max: int | None = None


class ColumnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scholarship_id: uuid.UUID
    name: str
    description: str | None
    field_type: ColumnFieldType
    select_options: list[str] | None
    is_required: bool
    ai_analyze: bool
    max_score: int
    input_min: int | None = None
    input_max: int | None = None
    order_index: int


class ColumnReorder(BaseModel):
    order: list[uuid.UUID]


class ScholarshipCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    deadline: datetime | None = None
    ai_analysis_enabled: bool = False
    blind_review_enabled: bool = False
    max_winners: int = Field(default=1, ge=1)
    ai_provider: LLMProvider = LLMProvider.CLAUDE
    ai_model: str | None = Field(default=None, max_length=200)

    _normalize_ai_model_field = field_validator("ai_model", mode="before")(_normalize_ai_model)


class ScholarshipUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    deadline: datetime | None = None
    ai_analysis_enabled: bool | None = None
    blind_review_enabled: bool | None = None
    max_winners: int | None = Field(default=None, ge=1)
    ai_provider: LLMProvider | None = None
    ai_model: str | None = Field(default=None, max_length=200)

    _normalize_ai_model_field = field_validator("ai_model", mode="before")(_normalize_ai_model)


class StatusUpdate(BaseModel):
    status: ScholarshipStatus


class ScholarshipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_by: uuid.UUID
    title: str
    description: str | None
    nizom_file_url: str | None
    status: ScholarshipStatus
    deadline: datetime | None
    ai_analysis_enabled: bool
    blind_review_enabled: bool
    max_winners: int
    ai_provider: LLMProvider
    ai_model: str | None
    created_at: datetime
    updated_at: datetime

    @field_validator("nizom_file_url", mode="before")
    @classmethod
    def _presign_nizom_file_url(cls, value: str | None) -> str | None:
        return build_file_download_url(value)


class ScholarshipDetail(ScholarshipOut):
    columns: list[ColumnOut] = Field(default_factory=list)


class JuryAssignRequest(BaseModel):
    jury_id: uuid.UUID


class JuryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
