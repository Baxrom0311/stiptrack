from __future__ import annotations

import uuid
from typing import Any
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AIJobStatus, AIJobType


class AIJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_type: AIJobType
    ref_id: uuid.UUID
    model_used: str | None
    status: AIJobStatus
    result: dict | None
    error_msg: str | None
    created_at: datetime
    finished_at: datetime | None


class GenerateColumnsRequest(BaseModel):
    purpose: str
    requirements: list[str]
    evaluation_criteria: list[str | dict[str, Any]]
    additional_docs: list[str] = Field(default_factory=list)
    total_max_score: int = Field(default=0, ge=0)
    scoring_type: str = "table"
    eligible_students: str | None = None
    selection_stages: str | None = None
