"""add scholarship templates

Revision ID: 202603210001
Revises: 202603200002
Create Date: 2026-03-21 09:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "202603210001"
down_revision = "202603200002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scholarship_templates",
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_scholarship_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["source_scholarship_id"], ["scholarships.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scholarship_templates_created_by"), "scholarship_templates", ["created_by"], unique=False)
    op.create_index(
        op.f("ix_scholarship_templates_source_scholarship_id"),
        "scholarship_templates",
        ["source_scholarship_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_scholarship_templates_source_scholarship_id"), table_name="scholarship_templates")
    op.drop_index(op.f("ix_scholarship_templates_created_by"), table_name="scholarship_templates")
    op.drop_table("scholarship_templates")
