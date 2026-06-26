"""add status to agent shift adherence

Revision ID: 20260618_0010
Revises: 20260618_0009
Create Date: 2026-06-18
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260618_0010"
down_revision: str | None = "20260618_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_shift_adherence",
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="",
            nullable=False,
        ),
    )
    op.alter_column("agent_shift_adherence", "status", server_default=None)


def downgrade() -> None:
    op.drop_column("agent_shift_adherence", "status")
