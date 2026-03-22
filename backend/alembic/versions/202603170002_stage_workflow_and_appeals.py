"""add scholarship stages, stage tasks and appeals

Revision ID: 202603170002
Revises: 202603170001
Create Date: 2026-03-17 13:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "202603170002"
down_revision = "202603170001"
branch_labels = None
depends_on = None


scholarship_stage_type_enum = sa.Enum(
    "application",
    "review",
    "exam",
    "interview",
    "final_decision",
    "appeal",
    name="scholarship_stage_type",
    native_enum=False,
)
stage_task_status_enum = sa.Enum(
    "todo",
    "in_progress",
    "done",
    "canceled",
    name="stage_task_status",
    native_enum=False,
)
appeal_status_enum = sa.Enum(
    "submitted",
    "under_review",
    "accepted",
    "rejected",
    name="appeal_status",
    native_enum=False,
)
user_role_enum = sa.Enum("admin", "jury", "student", name="user_role", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "scholarship_stages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scholarship_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("stage_type", scholarship_stage_type_enum, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["scholarship_id"], ["scholarships.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scholarship_id", "order_index", name="uq_stage_scholarship_order"),
    )
    op.create_index("idx_stages_scholarship", "scholarship_stages", ["scholarship_id"], unique=False)
    op.create_index("idx_stages_type", "scholarship_stages", ["stage_type"], unique=False)

    op.create_table(
        "stage_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_role", user_role_enum, nullable=True),
        sa.Column("status", stage_task_status_enum, nullable=False, server_default="todo"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"]),
        sa.ForeignKeyConstraint(["stage_id"], ["scholarship_stages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_stage_tasks_stage", "stage_tasks", ["stage_id"], unique=False)
    op.create_index("idx_stage_tasks_status", "stage_tasks", ["status"], unique=False)

    op.create_table(
        "appeals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scholarship_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", appeal_status_enum, nullable=False, server_default="submitted"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("attachment_url", sa.Text(), nullable=True),
        sa.Column("filed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("score_before", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("score_after", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["scholarship_id"], ["scholarships.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", "student_id", name="uq_appeal_application_student"),
    )
    op.create_index("idx_appeals_application", "appeals", ["application_id"], unique=False)
    op.create_index("idx_appeals_scholarship", "appeals", ["scholarship_id"], unique=False)
    op.create_index("idx_appeals_status", "appeals", ["status"], unique=False)
    op.create_index("idx_appeals_student", "appeals", ["student_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_appeals_student", table_name="appeals")
    op.drop_index("idx_appeals_status", table_name="appeals")
    op.drop_index("idx_appeals_scholarship", table_name="appeals")
    op.drop_index("idx_appeals_application", table_name="appeals")
    op.drop_table("appeals")

    op.drop_index("idx_stage_tasks_status", table_name="stage_tasks")
    op.drop_index("idx_stage_tasks_stage", table_name="stage_tasks")
    op.drop_table("stage_tasks")

    op.drop_index("idx_stages_type", table_name="scholarship_stages")
    op.drop_index("idx_stages_scholarship", table_name="scholarship_stages")
    op.drop_table("scholarship_stages")

    appeal_status_enum.drop(op.get_bind(), checkfirst=False)
    stage_task_status_enum.drop(op.get_bind(), checkfirst=False)
    scholarship_stage_type_enum.drop(op.get_bind(), checkfirst=False)
