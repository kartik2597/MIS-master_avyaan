"""add file_hash to upload_history

Stores a SHA-256 of each uploaded file so the same file cannot be uploaded and
processed twice by accident. Older uploads keep a null hash and are never
treated as duplicates.

Revision ID: 20261103_0015
Revises: 20261103_0014
Create Date: 2026-11-03
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261103_0015"
down_revision: str | None = "20261103_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "upload_history",
        sa.Column("file_hash", sa.String(length=64), nullable=True),
    )
    op.create_index(
        op.f("ix_upload_history_file_hash"),
        "upload_history",
        ["file_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_upload_history_file_hash"), table_name="upload_history")
    op.drop_column("upload_history", "file_hash")
