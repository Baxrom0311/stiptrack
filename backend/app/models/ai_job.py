from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin
from app.models.enums import AIJobStatus, AIJobType


class AIJob(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ai_jobs"

    job_type: Mapped[AIJobType] = mapped_column(
        SQLEnum(AIJobType, name="ai_job_type", native_enum=False), nullable=False
    )
    ref_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    model_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AIJobStatus] = mapped_column(
        SQLEnum(AIJobStatus, name="ai_job_status", native_enum=False),
        nullable=False,
        default=AIJobStatus.PENDING,
        index=True,
    )
    input_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
