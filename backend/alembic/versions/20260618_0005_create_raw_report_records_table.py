"""create raw report records table

Revision ID: 20260618_0005
Revises: 20260618_0004
Create Date: 2026-06-18
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260618_0005"
down_revision: str | None = "20260618_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "raw_report_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_type", sa.String(length=100), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["upload_id"], ["upload_history.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_raw_report_records_report_type"), "raw_report_records", ["report_type"])
    op.create_index(op.f("ix_raw_report_records_upload_id"), "raw_report_records", ["upload_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_raw_report_records_upload_id"), table_name="raw_report_records")
    op.drop_index(op.f("ix_raw_report_records_report_type"), table_name="raw_report_records")
    op.drop_table("raw_report_records")
