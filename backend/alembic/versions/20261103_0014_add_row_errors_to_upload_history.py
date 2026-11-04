"""add row_errors to upload_history

Stores the rows an import skipped (row number and reason) so the Validation
Report page can show and export all of them, not just the first ten that fit in
the short error_message summary.

Revision ID: 20261103_0014
Revises: 20261103_0013
Create Date: 2026-11-03
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261103_0014"
down_revision: str | None = "20261103_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "upload_history",
        sa.Column("row_errors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("upload_history", "row_errors")
