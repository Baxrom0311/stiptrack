from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AchievementType, ApplicationStatus


class Application(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("scholarship_id", "student_id", name="uq_app_scholarship_student"),)

    scholarship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scholarships.id"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    supervisor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus, name="application_status", native_enum=False),
        nullable=False,
        default=ApplicationStatus.DRAFT,
        index=True,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_score: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)

    scholarship = relationship("Scholarship", back_populates="applications")
    student = relationship("User", back_populates="student_applications", foreign_keys=[student_id])
    supervisor = relationship("User", back_populates="supervised_applications", foreign_keys=[supervisor_id])

    values = relationship("ApplicationValue", back_populates="application", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="application", cascade="all, delete-orphan")
    appeals = relationship("Appeal", back_populates="application", cascade="all, delete-orphan")
    status_logs = relationship("ApplicationStatusLog", back_populates="application", cascade="all, delete-orphan")


class ApplicationStatusLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "application_status_logs"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scholarship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scholarships.id"),
        nullable=False,
        index=True,
    )
    previous_status: Mapped[ApplicationStatus | None] = mapped_column(
        SQLEnum(ApplicationStatus, name="application_status", native_enum=False),
        nullable=True,
    )
    new_status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus, name="application_status", native_enum=False),
        nullable=False,
        index=True,
    )
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="system")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    application = relationship("Application", back_populates="status_logs")
    changed_by_user = relationship("User", foreign_keys=[changed_by])


class ApplicationValue(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "application_values"
    __table_args__ = (UniqueConstraint("application_id", "column_id", name="uq_application_column"),)

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    column_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scholarship_columns.id"), nullable=False
    )
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_score: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    plagiarism_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    plagiarism_matches: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    plagiarism_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    application = relationship("Application", back_populates="values")
    column = relationship("ScholarshipColumn", back_populates="values")


class StudentAchievement(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "student_achievements"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    type: Mapped[AchievementType | None] = mapped_column(
        SQLEnum(AchievementType, name="achievement_type", native_enum=False), nullable=True
    )
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    student = relationship("User", back_populates="achievements")
