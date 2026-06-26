"""create agent daily performance table

Revision ID: 20260618_0006
Revises: 20260618_0005
Create Date: 2026-06-18
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260618_0006"
down_revision: str | None = "20260618_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_daily_performance",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("emp_id", sa.String(length=50), nullable=False),
        sa.Column("employee_name", sa.String(length=255), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("campaign", sa.String(length=100), nullable=False),
        sa.Column("user_group", sa.String(length=100), nullable=False),
        sa.Column("attendance", sa.String(length=50), nullable=False),
        sa.Column("login_hours", sa.Numeric(10, 2), nullable=False),
        sa.Column("staff_time", sa.Numeric(10, 2), nullable=False),
        sa.Column("talk_time", sa.Numeric(10, 2), nullable=False),
        sa.Column("break_time", sa.Numeric(10, 2), nullable=False),
        sa.Column("idle_time", sa.Numeric(10, 2), nullable=False),
        sa.Column("productivity_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("total_calls", sa.Integer(), nullable=False),
        sa.Column("connected_calls", sa.Integer(), nullable=False),
        sa.Column("not_connected_calls", sa.Integer(), nullable=False),
        sa.Column("positive_calls", sa.Integer(), nullable=False),
        sa.Column("conversion_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_daily_performance_campaign"), "agent_daily_performance", ["campaign"])
    op.create_index(op.f("ix_agent_daily_performance_emp_id"), "agent_daily_performance", ["emp_id"])
    op.create_index(op.f("ix_agent_daily_performance_report_date"), "agent_daily_performance", ["report_date"])


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_daily_performance_report_date"), table_name="agent_daily_performance")
    op.drop_index(op.f("ix_agent_daily_performance_emp_id"), table_name="agent_daily_performance")
    op.drop_index(op.f("ix_agent_daily_performance_campaign"), table_name="agent_daily_performance")
    op.drop_table("agent_daily_performance")
