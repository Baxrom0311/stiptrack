"""initial schema

Revision ID: 202603170001
Revises:
Create Date: 2026-03-17 03:05:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "202603170001"
down_revision = None
branch_labels = None
depends_on = None


user_role_enum = sa.Enum("admin", "jury", "student", name="user_role", native_enum=False)
scholarship_status_enum = sa.Enum(
    "draft", "open", "closed", "done", name="scholarship_status", native_enum=False
)
column_field_type_enum = sa.Enum(
    "text",
    "textarea",
    "file",
    "number",
    "date",
    "select",
    "url",
    name="column_field_type",
    native_enum=False,
)
application_status_enum = sa.Enum(
    "draft", "submitted", "in_review", "winner", "rejected", name="application_status", native_enum=False
)
achievement_type_enum = sa.Enum(
    "paper", "award", "project", "cert", "olympiad", "other", name="achievement_type", native_enum=False
)
ai_job_type_enum = sa.Enum(
    "column_gen", "app_analysis", "review_gen", name="ai_job_type", native_enum=False
)
ai_job_status_enum = sa.Enum("pending", "running", "done", "failed", name="ai_job_status", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("student_id", sa.String(length=50), nullable=True),
        sa.Column("is_supervisor", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_role", "users", ["role"], unique=False)

    op.create_table(
        "scholarships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("nizom_file_url", sa.Text(), nullable=True),
        sa.Column("status", scholarship_status_enum, nullable=False, server_default="draft"),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_analysis_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("max_winners", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
    )
    op.create_index("ix_scholarships_status", "scholarships", ["status"], unique=False)

    op.create_table(
        "scholarship_columns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("scholarship_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("field_type", column_field_type_enum, nullable=False),
        sa.Column("select_options", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ai_analyze", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("max_score", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["scholarship_id"], ["scholarships.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "idx_columns_scholarship", "scholarship_columns", ["scholarship_id"], unique=False
    )

    op.create_table(
        "jury_assignments",
        sa.Column("scholarship_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("jury_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["jury_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["scholarship_id"], ["scholarships.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("scholarship_id", "jury_id", name="pk_jury_assignments"),
    )

    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("scholarship_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supervisor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", application_status_enum, nullable=False, server_default="draft"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("total_score", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["scholarship_id"], ["scholarships.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["supervisor_id"], ["users.id"]),
        sa.UniqueConstraint("scholarship_id", "student_id", name="uq_app_scholarship_student"),
    )
    op.create_index("idx_applications_scholarship", "applications", ["scholarship_id"], unique=False)
    op.create_index("idx_applications_student", "applications", ["student_id"], unique=False)
    op.create_index("idx_applications_status", "applications", ["status"], unique=False)

    op.create_table(
        "application_values",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("column_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_file_url", sa.Text(), nullable=True),
        sa.Column("ai_analysis", sa.Text(), nullable=True),
        sa.Column("ai_score", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["column_id"], ["scholarship_columns.id"]),
        sa.UniqueConstraint("application_id", "column_id", name="uq_application_column"),
    )
    op.create_index(
        "idx_app_values_application", "application_values", ["application_id"], unique=False
    )

    op.create_table(
        "evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("jury_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("total_score", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("final_comment", sa.Text(), nullable=True),
        sa.Column("ai_generated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_submitted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.ForeignKeyConstraint(["jury_id"], ["users.id"]),
        sa.UniqueConstraint("application_id", "jury_id", name="uq_evaluation_app_jury"),
    )
    op.create_index("idx_evaluations_application", "evaluations", ["application_id"], unique=False)
    op.create_index("idx_evaluations_jury", "evaluations", ["jury_id"], unique=False)

    op.create_table(
        "student_achievements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("type", achievement_type_enum, nullable=True),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "idx_achievements_student", "student_achievements", ["student_id"], unique=False
    )

    op.create_table(
        "ai_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_type", ai_job_type_enum, nullable=False),
        sa.Column("ref_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_used", sa.Text(), nullable=True),
        sa.Column("status", ai_job_status_enum, nullable=False, server_default="pending"),
        sa.Column("input_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_ai_jobs_status", "ai_jobs", ["status"], unique=False)
    op.create_index("ix_ai_jobs_ref_id", "ai_jobs", ["ref_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ai_jobs_ref_id", table_name="ai_jobs")
    op.drop_index("idx_ai_jobs_status", table_name="ai_jobs")
    op.drop_table("ai_jobs")

    op.drop_index("idx_achievements_student", table_name="student_achievements")
    op.drop_table("student_achievements")

    op.drop_index("idx_evaluations_jury", table_name="evaluations")
    op.drop_index("idx_evaluations_application", table_name="evaluations")
    op.drop_table("evaluations")

    op.drop_index("idx_app_values_application", table_name="application_values")
    op.drop_table("application_values")

    op.drop_index("idx_applications_status", table_name="applications")
    op.drop_index("idx_applications_student", table_name="applications")
    op.drop_index("idx_applications_scholarship", table_name="applications")
    op.drop_table("applications")

    op.drop_table("jury_assignments")

    op.drop_index("idx_columns_scholarship", table_name="scholarship_columns")
    op.drop_table("scholarship_columns")

    op.drop_index("ix_scholarships_status", table_name="scholarships")
    op.drop_table("scholarships")

    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    ai_job_status_enum.drop(op.get_bind(), checkfirst=False)
    ai_job_type_enum.drop(op.get_bind(), checkfirst=False)
    achievement_type_enum.drop(op.get_bind(), checkfirst=False)
    application_status_enum.drop(op.get_bind(), checkfirst=False)
    column_field_type_enum.drop(op.get_bind(), checkfirst=False)
    scholarship_status_enum.drop(op.get_bind(), checkfirst=False)
    user_role_enum.drop(op.get_bind(), checkfirst=False)
