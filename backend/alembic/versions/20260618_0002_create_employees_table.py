"""create employees table

Revision ID: 20260618_0002
Revises: 20260618_0001
Create Date: 2026-06-18
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260618_0002"
down_revision: str | None = "20260618_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("emp_id", sa.String(length=50), nullable=False),
        sa.Column("employee_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("mobile", sa.String(length=30), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=False),
        sa.Column("process", sa.String(length=100), nullable=False),
        sa.Column("designation", sa.String(length=100), nullable=False),
        sa.Column("manager_name", sa.String(length=255), nullable=False),
        sa.Column("tl_name", sa.String(length=255), nullable=False),
        sa.Column("date_of_joining", sa.Date(), nullable=False),
        sa.Column("employment_status", sa.String(length=50), nullable=False),
        sa.Column("location", sa.String(length=100), nullable=False),
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
    op.create_index(op.f("ix_employees_department"), "employees", ["department"])
    op.create_index(op.f("ix_employees_emp_id"), "employees", ["emp_id"], unique=True)
    op.create_index(op.f("ix_employees_employee_name"), "employees", ["employee_name"])
    op.create_index(op.f("ix_employees_manager_name"), "employees", ["manager_name"])
    op.create_index(op.f("ix_employees_process"), "employees", ["process"])
    op.create_index(op.f("ix_employees_tl_name"), "employees", ["tl_name"])


def downgrade() -> None:
    op.drop_index(op.f("ix_employees_tl_name"), table_name="employees")
    op.drop_index(op.f("ix_employees_process"), table_name="employees")
    op.drop_index(op.f("ix_employees_manager_name"), table_name="employees")
    op.drop_index(op.f("ix_employees_employee_name"), table_name="employees")
    op.drop_index(op.f("ix_employees_emp_id"), table_name="employees")
    op.drop_index(op.f("ix_employees_department"), table_name="employees")
    op.drop_table("employees")
