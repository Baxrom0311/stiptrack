"""add plagiarism fields to application values

Revision ID: 202603210003
Revises: 202603210002
Create Date: 2026-03-21 11:05:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "202603210003"
down_revision = "202603210002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("application_values", sa.Column("plagiarism_score", sa.Numeric(precision=5, scale=2), nullable=True))
    op.add_column(
        "application_values",
        sa.Column("plagiarism_matches", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("application_values", sa.Column("plagiarism_checked_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("application_values", "plagiarism_checked_at")
    op.drop_column("application_values", "plagiarism_matches")
    op.drop_column("application_values", "plagiarism_score")
