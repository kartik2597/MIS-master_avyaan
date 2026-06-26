"""add call breakdown to agent daily performance

Revision ID: 20260618_0009
Revises: 20260618_0008
Create Date: 2026-06-18
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260618_0009"
down_revision: str | None = "20260618_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_daily_performance",
        sa.Column(
            "dialer_total_calls",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "agent_daily_performance",
        sa.Column(
            "dialflow_total_calls",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "agent_daily_performance",
        sa.Column(
            "tl_remark",
            sa.String(length=500),
            server_default="",
            nullable=False,
        ),
    )
    op.alter_column(
        "agent_daily_performance",
        "dialer_total_calls",
        server_default=None,
    )
    op.alter_column(
        "agent_daily_performance",
        "dialflow_total_calls",
        server_default=None,
    )
    op.alter_column("agent_daily_performance", "tl_remark", server_default=None)


def downgrade() -> None:
    op.drop_column("agent_daily_performance", "tl_remark")
    op.drop_column("agent_daily_performance", "dialflow_total_calls")
    op.drop_column("agent_daily_performance", "dialer_total_calls")
