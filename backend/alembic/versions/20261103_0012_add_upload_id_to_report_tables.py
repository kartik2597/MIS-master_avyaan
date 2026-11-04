"""add upload_id to report tables

Links every imported row back to the upload that last wrote it, so deleting an
upload from the history also removes the data it created.

Rows imported before this migration have no upload_id (NULL) and cannot be
traced back to an upload, so deleting those uploads will not remove them.

Revision ID: 20261103_0012
Revises: 20261102_0011
Create Date: 2026-11-03
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261103_0012"
down_revision: str | None = "20261102_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "agent_daily_performance",
    "agent_shift_adherence",
    "agent_shrinkage",
    "employees",
)


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column("upload_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            f"fk_{table}_upload_id_upload_history",
            table,
            "upload_history",
            ["upload_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_index(f"ix_{table}_upload_id", table, ["upload_id"])


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_index(f"ix_{table}_upload_id", table_name=table)
        op.drop_constraint(
            f"fk_{table}_upload_id_upload_history", table, type_="foreignkey"
        )
        op.drop_column(table, "upload_id")
