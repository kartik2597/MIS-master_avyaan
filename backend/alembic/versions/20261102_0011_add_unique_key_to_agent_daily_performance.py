"""add unique key to agent daily performance

Revision ID: 20261102_0011
Revises: 20260618_0010
Create Date: 2026-11-02
"""
from collections.abc import Sequence

from alembic import op


revision: str = "20261102_0011"
down_revision: str | None = "20260618_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "uq_agent_daily_performance_emp_date_campaign"


def upgrade() -> None:
    # Keep only the most recently updated row for each agent/date/campaign so
    # the unique constraint can be created on databases that already hold
    # duplicates from earlier uploads.
    op.execute(
        """
        DELETE FROM agent_daily_performance AS older
        USING agent_daily_performance AS newer
        WHERE older.emp_id = newer.emp_id
          AND older.report_date = newer.report_date
          AND older.campaign = newer.campaign
          AND (older.updated_at, older.id) < (newer.updated_at, newer.id)
        """
    )
    op.create_unique_constraint(
        CONSTRAINT_NAME,
        "agent_daily_performance",
        ["emp_id", "report_date", "campaign"],
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "agent_daily_performance", type_="unique")
