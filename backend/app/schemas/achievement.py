from __future__ import annotations

import uuid
from datetime import date as DateType, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AchievementType
from app.services.file_service import build_file_download_url


class AchievementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    type: AchievementType | None = None
    date: DateType | None = None
    description: str | None = None


class AchievementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    type: AchievementType | None = None
    date: DateType | None = None
    description: str | None = None


class AchievementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    title: str
    type: AchievementType | None
    file_url: str | None
    date: DateType | None
    description: str | None
    created_at: datetime

    @field_validator("file_url", mode="before")
    @classmethod
    def _presign_file_url(cls, value: str | None) -> str | None:
        return build_file_download_url(value)
