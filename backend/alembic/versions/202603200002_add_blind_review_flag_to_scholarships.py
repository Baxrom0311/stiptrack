"""add blind review flag to scholarships

Revision ID: 202603200002
Revises: 202603200001
Create Date: 2026-03-20 11:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "202603200002"
down_revision = "202603200001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scholarships",
        sa.Column("blind_review_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("scholarships", "blind_review_enabled")
