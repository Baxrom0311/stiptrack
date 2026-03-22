"""add numeric bounds to scholarship columns

Revision ID: 202603190001
Revises: 202603170002
Create Date: 2026-03-19 18:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202603190001"
down_revision = "202603170002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scholarship_columns", sa.Column("input_min", sa.Integer(), nullable=True))
    op.add_column("scholarship_columns", sa.Column("input_max", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("scholarship_columns", "input_max")
    op.drop_column("scholarship_columns", "input_min")
