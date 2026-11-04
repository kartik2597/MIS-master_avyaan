"""add emp_id to users

Links a login to an employee (by Employee ID) so MANAGER and TL users can be
limited to their own team on the dashboards.

The column is a plain string, not a foreign key: employee rows are replaced
when a master database upload is re-imported or deleted, and that must not
touch user accounts.

Revision ID: 20261103_0013
Revises: 20261103_0012
Create Date: 2026-11-03
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261103_0013"
down_revision: str | None = "20261103_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("emp_id", sa.String(length=50), nullable=True))
    op.create_index("ix_users_emp_id", "users", ["emp_id"])


def downgrade() -> None:
    op.drop_index("ix_users_emp_id", table_name="users")
    op.drop_column("users", "emp_id")
