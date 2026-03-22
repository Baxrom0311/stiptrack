from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ColumnFieldType, LLMProvider, ScholarshipStatus


class Scholarship(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scholarships"

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    nizom_file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ScholarshipStatus] = mapped_column(
        SQLEnum(ScholarshipStatus, name="scholarship_status", native_enum=False),
        nullable=False,
        default=ScholarshipStatus.DRAFT,
        index=True,
    )
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_analysis_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    blind_review_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_winners: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    ai_provider: Mapped[LLMProvider] = mapped_column(
        SQLEnum(LLMProvider, name="llm_provider", native_enum=False),
        nullable=False,
        default=LLMProvider.CLAUDE,
    )
    ai_model: Mapped[str | None] = mapped_column(String(200), nullable=True)

    creator = relationship("User", back_populates="created_scholarships", foreign_keys=[created_by])
    columns = relationship(
        "ScholarshipColumn",
        back_populates="scholarship",
        cascade="all, delete-orphan",
        order_by="ScholarshipColumn.order_index",
    )
    jury_assignments = relationship(
        "JuryAssignment", back_populates="scholarship", cascade="all, delete-orphan"
    )
    applications = relationship("Application", back_populates="scholarship")
    stages = relationship(
        "ScholarshipStage",
        back_populates="scholarship",
        cascade="all, delete-orphan",
        order_by="ScholarshipStage.order_index",
    )
    appeals = relationship("Appeal", back_populates="scholarship", cascade="all, delete-orphan")
    templates = relationship("ScholarshipTemplate", back_populates="source_scholarship")


class ScholarshipColumn(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "scholarship_columns"

    scholarship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scholarships.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    field_type: Mapped[ColumnFieldType] = mapped_column(
        SQLEnum(ColumnFieldType, name="column_field_type", native_enum=False), nullable=False
    )
    select_options: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ai_analyze: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    input_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    scholarship = relationship("Scholarship", back_populates="columns")
    values = relationship("ApplicationValue", back_populates="column")


class JuryAssignment(Base):
    __tablename__ = "jury_assignments"

    scholarship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scholarships.id", ondelete="CASCADE"),
        primary_key=True,
    )
    jury_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    scholarship = relationship("Scholarship", back_populates="jury_assignments")
    jury = relationship("User", back_populates="jury_assignments", foreign_keys=[jury_id])


class ScholarshipTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scholarship_templates"

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    source_scholarship_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scholarships.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)

    source_scholarship = relationship("Scholarship", back_populates="templates")
    creator = relationship("User", foreign_keys=[created_by])
