from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EvaluationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | None
    application_id: uuid.UUID
    jury_id: uuid.UUID
    scores: dict[str, float]
    total_score: float | None
    final_comment: str | None
    ai_generated: bool
    is_submitted: bool
    submitted_at: datetime | None = None


class EvaluationUpdate(BaseModel):
    scores: dict[str, float] | None = None
    final_comment: str | None = None
    ai_generated: bool | None = None


class AIReviewRequest(BaseModel):
    jury_notes: str | None = None


class AIReviewResponse(BaseModel):
    review_text: str
    summary: str
    recommendation_note: str
    total_score: float
    max_total_score: float
    score_percent: float
