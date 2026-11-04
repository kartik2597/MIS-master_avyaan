from datetime import date

from pydantic import BaseModel, Field


class LeadershipSummary(BaseModel):
    """The headline numbers for leadership. Percentages are 0-100 and may pass 100
    for utilization when people log more than the standard working hours."""

    # With no dates asked for, the latest 30 days that have timesheet or hiring data.
    date_from: date | None = None
    date_to: date | None = None
    # False when none of the source reports has any data for the period.
    has_data: bool = False

    # Hours logged on projects as a share of the hours people were available for:
    # active employees x working days (Mon-Fri) x the standard day length.
    # None when no timesheet or no employee master is available for the period.
    utilization_percent: float | None = None
    logged_hours: float = Field(default=0.0, ge=0)
    capacity_hours: float = Field(default=0.0, ge=0)
    working_days: int = Field(default=0, ge=0)
    employees_in_scope: int = Field(default=0, ge=0)
    standard_daily_hours: float = Field(default=0.0, ge=0)

    # Billable hours as a share of all logged hours. None when no timesheet.
    billable_percent: float | None = None
    billable_hours: float = Field(default=0.0, ge=0)

    # Leavers as a share of the average of opening and closing headcount.
    # None when there is no hiring/attrition data or no headcount to compare against.
    attrition_percent: float | None = None
    leavers: int = Field(default=0, ge=0)
    opening_headcount: int | None = None
    closing_headcount: int | None = None

    # No report in the application carries SLA data yet, so this stays empty and
    # the UI shows "No data" until an SLA report is added.
    sla_percent: float | None = None
    sla_available: bool = False

    # Report types with no rows for the period. Their cards have no real data.
    missing_reports: list[str] = Field(default_factory=list)
