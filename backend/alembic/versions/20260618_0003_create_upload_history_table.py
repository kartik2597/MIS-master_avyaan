"""create upload history table

Revision ID: 20260618_0003
Revises: 20260618_0002
Create Date: 2026-06-18
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260618_0003"
down_revision: str | None = "20260618_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "upload_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("original_file_name", sa.String(length=255), nullable=False),
        sa.Column("report_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("upload_status", sa.String(length=50), nullable=False),
        sa.Column("total_records", sa.Integer(), nullable=False),
        sa.Column("processed_records", sa.Integer(), nullable=False),
        sa.Column("failed_records", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_upload_history_report_type"), "upload_history", ["report_type"])
    op.create_index(op.f("ix_upload_history_upload_status"), "upload_history", ["upload_status"])
    op.create_index(op.f("ix_upload_history_uploaded_by"), "upload_history", ["uploaded_by"])


def downgrade() -> None:
    op.drop_index(op.f("ix_upload_history_uploaded_by"), table_name="upload_history")
    op.drop_index(op.f("ix_upload_history_upload_status"), table_name="upload_history")
    op.drop_index(op.f("ix_upload_history_report_type"), table_name="upload_history")
    op.drop_table("upload_history")
