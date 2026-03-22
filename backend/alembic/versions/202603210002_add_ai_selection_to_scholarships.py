"""add scholarship ai selection

Revision ID: 202603210002
Revises: 202603210001
Create Date: 2026-03-21 10:15:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "202603210002"
down_revision = "202603210001"
branch_labels = None
depends_on = None


llm_provider_enum = sa.Enum(
    "claude",
    "openai",
    "gemini",
    "ollama",
    "deepseek",
    name="llm_provider",
    native_enum=False,
)


def upgrade() -> None:
    op.add_column(
        "scholarships",
        sa.Column(
            "ai_provider",
            llm_provider_enum,
            nullable=False,
            server_default="claude",
        ),
    )
    op.add_column("scholarships", sa.Column("ai_model", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("scholarships", "ai_model")
    op.drop_column("scholarships", "ai_provider")
