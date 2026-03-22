"""add application status logs

Revision ID: 202603200001
Revises: 202603190001
Create Date: 2026-03-20 00:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "202603200001"
down_revision = "202603190001"
branch_labels = None
depends_on = None


application_status_enum = sa.Enum(
    "draft", "submitted", "in_review", "winner", "rejected", name="application_status", native_enum=False
)


def upgrade() -> None:
    op.create_table(
        "application_status_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scholarship_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_status", application_status_enum, nullable=True),
        sa.Column("new_status", application_status_enum, nullable=False),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="system"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scholarship_id"], ["scholarships.id"]),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"]),
    )
    op.create_index("idx_app_status_logs_application", "application_status_logs", ["application_id"], unique=False)
    op.create_index("idx_app_status_logs_scholarship", "application_status_logs", ["scholarship_id"], unique=False)
    op.create_index("idx_app_status_logs_new_status", "application_status_logs", ["new_status"], unique=False)
    op.create_index("idx_app_status_logs_changed_by", "application_status_logs", ["changed_by"], unique=False)
    op.create_index("idx_app_status_logs_created_at", "application_status_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_app_status_logs_created_at", table_name="application_status_logs")
    op.drop_index("idx_app_status_logs_changed_by", table_name="application_status_logs")
    op.drop_index("idx_app_status_logs_new_status", table_name="application_status_logs")
    op.drop_index("idx_app_status_logs_scholarship", table_name="application_status_logs")
    op.drop_index("idx_app_status_logs_application", table_name="application_status_logs")
    op.drop_table("application_status_logs")
