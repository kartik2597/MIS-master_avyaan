"""create project timesheet and employee movement tables

- project_timesheets: hours per employee, project and day (PROJECT_TIMESHEET report).
- employee_movements: joiners and leavers (HIRING_ATTRITION report).

Both link back to the upload that wrote each row (ON DELETE CASCADE), so deleting
an upload from the history also removes the data it created.

Revision ID: 20261104_0017
Revises: 20261103_0016
Create Date: 2026-11-04
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261104_0017"
down_revision: str | None = "20261103_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_timesheets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "upload_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("upload_history.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("emp_id", sa.String(50), nullable=False),
        sa.Column("employee_name", sa.String(255), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("project_name", sa.String(150), nullable=False),
        sa.Column("client_name", sa.String(150), nullable=False),
        sa.Column("task_type", sa.String(100), nullable=False),
        sa.Column("billable", sa.Boolean(), nullable=False),
        sa.Column("hours", sa.Numeric(6, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "emp_id",
            "report_date",
            "project_name",
            "task_type",
            name="uq_project_timesheets_entry",
        ),
    )
    op.create_index("ix_project_timesheets_upload_id", "project_timesheets", ["upload_id"])
    op.create_index("ix_project_timesheets_emp_id", "project_timesheets", ["emp_id"])
    op.create_index("ix_project_timesheets_report_date", "project_timesheets", ["report_date"])
    op.create_index("ix_project_timesheets_project_name", "project_timesheets", ["project_name"])

    op.create_table(
        "employee_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "upload_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("upload_history.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("emp_id", sa.String(50), nullable=False),
        sa.Column("employee_name", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("team", sa.String(100), nullable=False),
        sa.Column("designation", sa.String(100), nullable=False),
        sa.Column("manager_name", sa.String(255), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("hiring_source", sa.String(150), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "emp_id",
            "event_type",
            "report_date",
            name="uq_employee_movements_event",
        ),
    )
    op.create_index("ix_employee_movements_upload_id", "employee_movements", ["upload_id"])
    op.create_index("ix_employee_movements_emp_id", "employee_movements", ["emp_id"])
    op.create_index("ix_employee_movements_event_type", "employee_movements", ["event_type"])
    op.create_index("ix_employee_movements_report_date", "employee_movements", ["report_date"])
    op.create_index("ix_employee_movements_team", "employee_movements", ["team"])


def downgrade() -> None:
    op.drop_table("employee_movements")
    op.drop_table("project_timesheets")
