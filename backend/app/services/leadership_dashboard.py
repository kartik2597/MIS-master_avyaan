"""Leadership dashboard: utilization, billable, attrition and SLA on one view.

The numbers are built from the same functions the Project & Timesheet and Hiring &
Attrition dashboards use, so the leadership view always agrees with them. It takes
the same `scope` as the other dashboards (a query of Employee IDs, or None for no
limit), so a MANAGER or TL only ever sees the numbers for their own team.
"""

from datetime import date, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.employee_movement import EmployeeMovement
from app.models.project_timesheet import ProjectTimesheet
from app.reports.report_types import ReportType
from app.schemas.leadership_dashboard import LeadershipSummary
from app.services.hiring_dashboard import get_hiring_summary
from app.services.project_dashboard import EXITED_STATUSES, get_project_summary


# With no dates given, the view covers this many days ending on the newest day that
# has a timesheet or hiring/attrition row.
DEFAULT_WINDOW_DAYS = 30

# The length of a full working day, used to work out how many hours people were
# available for. Utilization = hours logged / (employees x working days x this).
STANDARD_DAILY_HOURS = 8.0

# Monday to Friday are working days (date.weekday() is 0 for Monday, 5 for Saturday).
LAST_WORKING_WEEKDAY = 4


def resolve_period(
    db: Session,
    date_from: date | None,
    date_to: date | None,
) -> tuple[date | None, date | None]:
    """The dates the view describes. Both ends are always filled in when there is data,
    because capacity needs a start and an end to count working days."""
    end = date_to
    if end is None:
        latest = [
            db.scalar(select(func.max(ProjectTimesheet.report_date))),
            db.scalar(select(func.max(EmployeeMovement.report_date))),
        ]
        latest = [day for day in latest if day is not None]
        if not latest:
            return date_from, None
        end = max(latest)
    if date_from is not None:
        # A start date after the newest data (and no end date) is a one-day window.
        return date_from, max(end, date_from)
    return end - timedelta(days=DEFAULT_WINDOW_DAYS - 1), end


def count_working_days(start: date, end: date) -> int:
    """Monday-to-Friday days from start to end, both included."""
    if end < start:
        return 0
    return sum(
        1
        for offset in range((end - start).days + 1)
        if (start + timedelta(days=offset)).weekday() <= LAST_WORKING_WEEKDAY
    )


def _employees_in_scope(db: Session, end: date, scope: Select | None) -> int:
    """Employees still with the company who had joined by the end of the period."""
    conditions = [
        func.lower(Employee.employment_status).not_in(EXITED_STATUSES),
        Employee.date_of_joining <= end,
    ]
    if scope is not None:
        conditions.append(Employee.emp_id.in_(scope))
    return int(db.scalar(select(func.count()).select_from(Employee).where(*conditions)) or 0)


def get_leadership_summary(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    scope: Select | None = None,
) -> LeadershipSummary:
    start, end = resolve_period(db, date_from, date_to)
    if start is None or end is None:
        return LeadershipSummary(
            date_from=start,
            date_to=end,
            standard_daily_hours=STANDARD_DAILY_HOURS,
            missing_reports=[
                ReportType.PROJECT_TIMESHEET.value,
                ReportType.HIRING_ATTRITION.value,
            ],
        )

    projects = get_project_summary(db, date_from=start, date_to=end, scope=scope)
    hiring = get_hiring_summary(db, date_from=start, date_to=end, scope=scope)

    employees = _employees_in_scope(db, end, scope)
    working_days = count_working_days(start, end)
    capacity = round(employees * working_days * STANDARD_DAILY_HOURS, 2)
    utilization: float | None = None
    if projects.has_data and capacity > 0:
        utilization = round(projects.total_hours * 100 / capacity, 2)

    missing_reports: list[str] = []
    if not projects.has_data:
        missing_reports.append(ReportType.PROJECT_TIMESHEET.value)
    if not hiring.has_data:
        missing_reports.append(ReportType.HIRING_ATTRITION.value)
    if employees == 0:
        # Utilization and attrition both need the employee master for headcount.
        missing_reports.append(ReportType.MASTER_DATABASE.value)

    return LeadershipSummary(
        date_from=start,
        date_to=end,
        has_data=projects.has_data or hiring.has_data,
        utilization_percent=utilization,
        logged_hours=projects.total_hours,
        capacity_hours=capacity,
        working_days=working_days,
        employees_in_scope=employees,
        standard_daily_hours=STANDARD_DAILY_HOURS,
        billable_percent=projects.billable_percent,
        billable_hours=projects.billable_hours,
        attrition_percent=hiring.attrition_percent,
        leavers=hiring.leavers,
        opening_headcount=hiring.opening_headcount,
        closing_headcount=hiring.closing_headcount,
        sla_percent=None,
        sla_available=False,
        missing_reports=missing_reports,
    )
