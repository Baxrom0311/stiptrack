from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AppealStatus, ScholarshipStageType, StageTaskStatus, UserRole


class ScholarshipStage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scholarship_stages"
    __table_args__ = (
        UniqueConstraint("scholarship_id", "order_index", name="uq_stage_scholarship_order"),
    )

    scholarship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scholarships.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    stage_type: Mapped[ScholarshipStageType] = mapped_column(
        SQLEnum(ScholarshipStageType, name="scholarship_stage_type", native_enum=False),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    scholarship = relationship("Scholarship", back_populates="stages")
    tasks = relationship("StageTask", back_populates="stage", cascade="all, delete-orphan")


class StageTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stage_tasks"

    stage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scholarship_stages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    assigned_role: Mapped[UserRole | None] = mapped_column(
        SQLEnum(UserRole, name="user_role", native_enum=False),
        nullable=True,
    )
    status: Mapped[StageTaskStatus] = mapped_column(
        SQLEnum(StageTaskStatus, name="stage_task_status", native_enum=False),
        nullable=False,
        default=StageTaskStatus.TODO,
        index=True,
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    stage = relationship("ScholarshipStage", back_populates="tasks")
    assignee = relationship("User", foreign_keys=[assigned_to])


class Appeal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "appeals"
    __table_args__ = (
        UniqueConstraint("application_id", "student_id", name="uq_appeal_application_student"),
    )

    scholarship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scholarships.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    status: Mapped[AppealStatus] = mapped_column(
        SQLEnum(AppealStatus, name="appeal_status", native_enum=False),
        nullable=False,
        default=AppealStatus.SUBMITTED,
        index=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    filed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    score_before: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    score_after: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)

    scholarship = relationship("Scholarship", back_populates="appeals")
    application = relationship("Application", back_populates="appeals")
    student = relationship("User", foreign_keys=[student_id], back_populates="appeals")
    resolver = relationship("User", foreign_keys=[resolved_by], back_populates="resolved_appeals")
