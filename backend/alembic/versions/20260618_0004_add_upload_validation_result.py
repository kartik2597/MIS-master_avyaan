"""add upload validation result

Revision ID: 20260618_0004
Revises: 20260618_0003
Create Date: 2026-06-18
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260618_0004"
down_revision: str | None = "20260618_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "upload_history",
        sa.Column("validation_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("upload_history", "validation_result")
