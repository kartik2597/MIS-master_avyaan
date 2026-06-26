"""create agent shrinkage table

Revision ID: 20260618_0008
Revises: 20260618_0007
Create Date: 2026-06-18
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260618_0008"
down_revision: str | None = "20260618_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_shrinkage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("emp_id", sa.String(length=50), nullable=False),
        sa.Column("employee_name", sa.String(length=255), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("process", sa.String(length=100), nullable=False),
        sa.Column("designation", sa.String(length=100), nullable=False),
        sa.Column("manager_name", sa.String(length=255), nullable=False),
        sa.Column("date_of_joining", sa.Date(), nullable=False),
        sa.Column("login_hours_seconds", sa.Integer(), nullable=False),
        sa.Column("attendance", sa.String(length=50), nullable=False),
        sa.Column("employee_age_days", sa.Integer(), nullable=False),
        sa.Column("tenure_bucket", sa.String(length=50), nullable=False),
        sa.Column("agent_count", sa.Integer(), nullable=False),
        sa.Column("present_count", sa.Integer(), nullable=False),
        sa.Column("absent_count", sa.Integer(), nullable=False),
        sa.Column("lwp_count", sa.Integer(), nullable=False),
        sa.Column("cl_count", sa.Integer(), nullable=False),
        sa.Column("half_day_count", sa.Integer(), nullable=False),
        sa.Column("training_count", sa.Integer(), nullable=False),
        sa.Column("planned_shrinkage", sa.Numeric(5, 2), nullable=False),
        sa.Column("unplanned_shrinkage", sa.Numeric(5, 2), nullable=False),
        sa.Column("opening_headcount", sa.Integer(), nullable=False),
        sa.Column("closing_headcount", sa.Integer(), nullable=False),
        sa.Column("attrition", sa.Integer(), nullable=False),
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
            name="uq_agent_shrinkage_emp_report_date",
        ),
    )
    op.create_index(op.f("ix_agent_shrinkage_emp_id"), "agent_shrinkage", ["emp_id"])
    op.create_index(
        op.f("ix_agent_shrinkage_manager_name"),
        "agent_shrinkage",
        ["manager_name"],
    )
    op.create_index(op.f("ix_agent_shrinkage_process"), "agent_shrinkage", ["process"])
    op.create_index(
        op.f("ix_agent_shrinkage_report_date"),
        "agent_shrinkage",
        ["report_date"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_shrinkage_report_date"), table_name="agent_shrinkage")
    op.drop_index(op.f("ix_agent_shrinkage_process"), table_name="agent_shrinkage")
    op.drop_index(op.f("ix_agent_shrinkage_manager_name"), table_name="agent_shrinkage")
    op.drop_index(op.f("ix_agent_shrinkage_emp_id"), table_name="agent_shrinkage")
    op.drop_table("agent_shrinkage")
