from __future__ import annotations

import uuid

from sqlalchemy import Boolean, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UserRole


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role", native_enum=False), nullable=False, index=True
    )
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    student_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_supervisor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_scholarships = relationship(
        "Scholarship", back_populates="creator", foreign_keys="Scholarship.created_by"
    )

    jury_assignments = relationship(
        "JuryAssignment", back_populates="jury", foreign_keys="JuryAssignment.jury_id"
    )

    student_applications = relationship(
        "Application", back_populates="student", foreign_keys="Application.student_id"
    )

    supervised_applications = relationship(
        "Application", back_populates="supervisor", foreign_keys="Application.supervisor_id"
    )

    evaluations = relationship(
        "Evaluation", back_populates="jury", foreign_keys="Evaluation.jury_id"
    )

    achievements = relationship(
        "StudentAchievement", back_populates="student", cascade="all, delete-orphan"
    )

    appeals = relationship(
        "Appeal",
        back_populates="student",
        foreign_keys="Appeal.student_id",
    )

    resolved_appeals = relationship(
        "Appeal",
        back_populates="resolver",
        foreign_keys="Appeal.resolved_by",
    )

    application_status_logs = relationship(
        "ApplicationStatusLog",
        foreign_keys="ApplicationStatusLog.changed_by",
        overlaps="changed_by_user",
    )
