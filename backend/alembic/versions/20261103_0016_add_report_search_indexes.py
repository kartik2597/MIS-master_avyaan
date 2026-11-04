"""add report indexes for dashboard speed

- A (report_date, emp_id) index on the three report tables, which is what the
  dashboard filters and joins on.
- pg_trgm GIN indexes on the APR emp_id and employee_name columns, so the agent
  search (ILIKE '%term%') does not scan the whole table.

The single-column report_date and emp_id indexes already exist from the model
definitions. Every statement uses IF NOT EXISTS, so this is safe to re-run.

CREATE EXTENSION needs a database role that may create extensions. If the app
user cannot, run `CREATE EXTENSION pg_trgm;` once as a superuser and then run
this migration.

Revision ID: 20261103_0016
Revises: 20261103_0015
Create Date: 2026-11-03
"""
from collections.abc import Sequence

from alembic import op


revision: str = "20261103_0016"
down_revision: str | None = "20261103_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


REPORT_TABLES = (
    "agent_daily_performance",
    "agent_shift_adherence",
    "agent_shrinkage",
)


def upgrade() -> None:
    for table in REPORT_TABLES:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{table}_report_date_emp_id "
            f"ON {table} (report_date, emp_id)"
        )

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_agent_daily_performance_emp_id_trgm "
        "ON agent_daily_performance USING gin (emp_id gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_agent_daily_performance_employee_name_trgm "
        "ON agent_daily_performance USING gin (employee_name gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_agent_daily_performance_employee_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_agent_daily_performance_emp_id_trgm")
    for table in REPORT_TABLES:
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_report_date_emp_id")
    # pg_trgm is left installed: other objects may use it.
