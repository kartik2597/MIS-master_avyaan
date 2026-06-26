"""create agent shift adherence table

Revision ID: 20260618_0007
Revises: 20260618_0006
Create Date: 2026-06-18
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260618_0007"
down_revision: str | None = "20260618_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_shift_adherence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("emp_id", sa.String(length=50), nullable=False),
        sa.Column("employee_name", sa.String(length=255), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("process", sa.String(length=100), nullable=False),
        sa.Column("designation", sa.String(length=100), nullable=False),
        sa.Column("manager_name", sa.String(length=255), nullable=False),
        sa.Column("attendance", sa.String(length=50), nullable=False),
        sa.Column("shift_start_time", sa.Time(), nullable=False),
        sa.Column("shift_end_time", sa.Time(), nullable=False),
        sa.Column("actual_login_time", sa.Time(), nullable=False),
        sa.Column("actual_logout_time", sa.Time(), nullable=False),
        sa.Column("login_hours_seconds", sa.Integer(), nullable=False),
        sa.Column("downtime_seconds", sa.Integer(), nullable=False),
        sa.Column("login_plus_downtime_seconds", sa.Integer(), nullable=False),
        sa.Column("shift_login_adherence_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("adherence_status", sa.String(length=50), nullable=False),
        sa.Column("late_login_minutes", sa.Integer(), nullable=False),
        sa.Column("early_logout_minutes", sa.Integer(), nullable=False),
        sa.Column("adherence_flag", sa.Boolean(), nullable=False),
        sa.Column("non_adherence_flag", sa.Boolean(), nullable=False),
        sa.Column("non_adherence_percent", sa.Numeric(5, 2), nullable=False),
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
        sa.UniqueConstraint(
            "emp_id",
            "report_date",
            name="uq_agent_shift_adherence_emp_report_date",
        ),
    )
    op.create_index(
        op.f("ix_agent_shift_adherence_emp_id"),
        "agent_shift_adherence",
        ["emp_id"],
    )
    op.create_index(
        op.f("ix_agent_shift_adherence_manager_name"),
        "agent_shift_adherence",
        ["manager_name"],
    )
    op.create_index(
        op.f("ix_agent_shift_adherence_process"),
        "agent_shift_adherence",
        ["process"],
    )
    op.create_index(
        op.f("ix_agent_shift_adherence_report_date"),
        "agent_shift_adherence",
        ["report_date"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_shift_adherence_report_date"), table_name="agent_shift_adherence")
    op.drop_index(op.f("ix_agent_shift_adherence_process"), table_name="agent_shift_adherence")
    op.drop_index(op.f("ix_agent_shift_adherence_manager_name"), table_name="agent_shift_adherence")
    op.drop_index(op.f("ix_agent_shift_adherence_emp_id"), table_name="agent_shift_adherence")
    op.drop_table("agent_shift_adherence")
