from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class DashboardKpis(BaseModel):
    head_count: int = Field(ge=0)
    present_count: int = Field(ge=0)
    late_login_count: int = Field(ge=0)
    early_logout_count: int = Field(ge=0)
    shift_adherence_count: int = Field(ge=0)
    non_adherence_count: int = Field(ge=0)
    planned_shrinkage: Decimal = Field(ge=0)
    unplanned_shrinkage: Decimal = Field(ge=0)
    overall_shrinkage: Decimal = Field(ge=0)
    attrition_count: int = Field(ge=0)
    total_talk_time: Decimal = Field(ge=0)
    total_login_time: Decimal = Field(ge=0)
    total_staff_time: Decimal = Field(ge=0)
    total_downtime: Decimal = Field(ge=0)
    total_idle_time: Decimal = Field(ge=0)
    total_break_time: Decimal = Field(ge=0)
    # The single day every card describes when no date range was requested.
    report_date: date | None = None
    # Report types (APR, SHIFT_ADHERENCE, SHRINKAGE) with no rows for the selected
    # day or range. Their cards have no real data, so the UI shows "No data"
    # instead of a 0 that looks like a real value.
    missing_reports: list[str] = Field(default_factory=list)


class DashboardFilterOptions(BaseModel):
    """Values the dashboard filter drop-downs can offer to the signed-in user."""

    processes: list[str] = Field(default_factory=list)
    managers: list[str] = Field(default_factory=list)
    tls: list[str] = Field(default_factory=list)


class DashboardTrendPoint(BaseModel):
    """One day on the trend charts. Times are in hours, percentages are 0-100."""

    report_date: date
    head_count: int = Field(ge=0)
    present_count: int = Field(ge=0)
    # None when no shift adherence rows exist for the day (so the chart shows a
    # gap instead of a misleading 0%).
    adherence_percent: float | None = None
    # None when no shrinkage rows exist for the day.
    overall_shrinkage: float | None = None
    talk_time: float = Field(ge=0)
    staff_time: float = Field(ge=0)


class DashboardTrends(BaseModel):
    points: list[DashboardTrendPoint] = Field(default_factory=list)


class AttendanceSlice(BaseModel):
    # Present, Absent, Leave, LWP, Half Day, Training or Other.
    status: str
    count: int = Field(ge=0)


class AttendanceBreakdown(BaseModel):
    slices: list[AttendanceSlice] = Field(default_factory=list)
    total: int = Field(ge=0)
    # The single day described when no date range was requested.
    report_date: date | None = None


class DashboardAgentRow(BaseModel):
    """One agent, rolled up over the selected day or range. Times are in hours."""

    emp_id: str
    employee_name: str
    process: str
    days_recorded: int = Field(ge=0)
    days_present: int = Field(ge=0)
    login_hours: float = Field(ge=0)
    talk_time: float = Field(ge=0)
    idle_time: float = Field(ge=0)
    break_time: float = Field(ge=0)
    late_logins: int = Field(ge=0)
    early_logouts: int = Field(ge=0)
    adherent_days: int = Field(ge=0)


class DashboardAgentList(BaseModel):
    items: list[DashboardAgentRow] = Field(default_factory=list)
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    report_date: date | None = None
