"""Project & timesheet dashboard: who logged how many hours on which project.

Every function takes the same `scope` as the agent dashboard (a query of Employee
IDs, or None for no limit), so a MANAGER or TL only ever sees their own team.
"""

from datetime import date, timedelta

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.project_timesheet import ProjectTimesheet
from app.schemas.project_dashboard import (
    BenchEmployeeRow,
    BenchList,
    ProjectEmployeeList,
    ProjectEmployeeRow,
    ProjectHoursList,
    ProjectHoursRow,
    ProjectSummary,
    ProjectTrendPoint,
    ProjectTrends,
)


# With no dates given, the dashboard covers this many days ending on the newest
# day that has timesheet rows.
DEFAULT_WINDOW_DAYS = 30

# Employment statuses that mean the person is no longer with the company, so they
# are never listed as "on the bench".
EXITED_STATUSES = (
    "resigned",
    "terminated",
    "left",
    "exited",
    "inactive",
    "absconded",
    "separated",
    "relieved",
)


def _hours(value: object) -> float:
    if value is None:
        return 0.0
    return round(float(value), 2)


def _percent(part: float, whole: float) -> float | None:
    return round(part * 100 / whole, 2) if whole > 0 else None


def resolve_period(
    db: Session,
    date_from: date | None,
    date_to: date | None,
) -> tuple[date | None, date | None]:
    """The dates the dashboard describes. Open ends stay open when dates are given."""
    if date_from is None and date_to is None:
        latest = db.scalar(select(func.max(ProjectTimesheet.report_date)))
        if latest is None:
            return None, None
        return latest - timedelta(days=DEFAULT_WINDOW_DAYS - 1), latest
    return date_from, date_to


def _filters(
    date_from: date | None,
    date_to: date | None,
    scope: Select | None,
) -> list:
    conditions = []
    if date_from is not None:
        conditions.append(ProjectTimesheet.report_date >= date_from)
    if date_to is not None:
        conditions.append(ProjectTimesheet.report_date <= date_to)
    if scope is not None:
        conditions.append(ProjectTimesheet.emp_id.in_(scope))
    return conditions


def _billable_hours():
    return func.coalesce(
        func.sum(case((ProjectTimesheet.billable.is_(True), ProjectTimesheet.hours), else_=0)),
        0,
    )


def get_project_summary(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    scope: Select | None = None,
) -> ProjectSummary:
    start, end = resolve_period(db, date_from, date_to)
    row = db.execute(
        select(
            func.count(ProjectTimesheet.id),
            func.coalesce(func.sum(ProjectTimesheet.hours), 0),
            _billable_hours(),
            func.count(func.distinct(ProjectTimesheet.emp_id)),
            func.count(func.distinct(ProjectTimesheet.project_name)),
        ).where(*_filters(start, end, scope))
    ).one()

    entries = int(row[0] or 0)
    total = _hours(row[1])
    billable = _hours(row[2])
    employees = int(row[3] or 0)
    return ProjectSummary(
        date_from=start,
        date_to=end,
        has_data=entries > 0,
        total_hours=total,
        billable_hours=billable,
        non_billable_hours=round(max(total - billable, 0), 2),
        billable_percent=_percent(billable, total),
        employees_logged=employees,
        active_projects=int(row[4] or 0),
        avg_hours_per_employee=round(total / employees, 2) if employees else 0.0,
    )


def get_project_hours(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    scope: Select | None = None,
    limit: int = 50,
) -> ProjectHoursList:
    """Hours per project, biggest first."""
    start, end = resolve_period(db, date_from, date_to)
    filters = _filters(start, end, scope)
    grand_total = _hours(
        db.scalar(
            select(func.coalesce(func.sum(ProjectTimesheet.hours), 0)).where(*filters)
        )
    )
    rows = db.execute(
        select(
            ProjectTimesheet.project_name,
            func.max(ProjectTimesheet.client_name),
            func.coalesce(func.sum(ProjectTimesheet.hours), 0),
            _billable_hours(),
            func.count(func.distinct(ProjectTimesheet.emp_id)),
        )
        .where(*filters)
        .group_by(ProjectTimesheet.project_name)
        .order_by(func.sum(ProjectTimesheet.hours).desc(), ProjectTimesheet.project_name)
        .limit(limit)
    ).all()

    return ProjectHoursList(
        date_from=start,
        date_to=end,
        items=[
            ProjectHoursRow(
                project_name=name,
                client_name=client or "",
                total_hours=_hours(total),
                billable_hours=_hours(billable),
                employees=int(people or 0),
                share_percent=_percent(_hours(total), grand_total) or 0.0,
            )
            for name, client, total, billable, people in rows
        ],
    )


def get_project_employees(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 10,
    scope: Select | None = None,
) -> ProjectEmployeeList:
    """One row per employee: hours, billable share, projects worked and days logged."""
    start, end = resolve_period(db, date_from, date_to)
    filters = _filters(start, end, scope)
    term = (search or "").strip()
    if term:
        pattern = f"%{term}%"
        filters.append(
            or_(
                ProjectTimesheet.emp_id.ilike(pattern),
                ProjectTimesheet.employee_name.ilike(pattern),
            )
        )

    per_employee = (
        select(
            ProjectTimesheet.emp_id.label("emp_id"),
            func.max(ProjectTimesheet.employee_name).label("employee_name"),
            func.coalesce(func.sum(ProjectTimesheet.hours), 0).label("total"),
            _billable_hours().label("billable"),
            func.count(func.distinct(ProjectTimesheet.project_name)).label("projects"),
            func.count(func.distinct(ProjectTimesheet.report_date)).label("days"),
        )
        .where(*filters)
        .group_by(ProjectTimesheet.emp_id)
    )
    total_rows = int(db.scalar(select(func.count()).select_from(per_employee.subquery())) or 0)
    rows = db.execute(
        per_employee.order_by(
            func.sum(ProjectTimesheet.hours).desc(), ProjectTimesheet.emp_id
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return ProjectEmployeeList(
        date_from=start,
        date_to=end,
        total=total_rows,
        page=page,
        page_size=page_size,
        items=[
            ProjectEmployeeRow(
                emp_id=row.emp_id,
                employee_name=row.employee_name,
                total_hours=_hours(row.total),
                billable_hours=_hours(row.billable),
                billable_percent=_percent(_hours(row.billable), _hours(row.total)),
                projects=int(row.projects or 0),
                days_logged=int(row.days or 0),
            )
            for row in rows
        ],
    )


def get_bench(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 10,
    scope: Select | None = None,
) -> BenchList:
    """Active employees in the viewer's scope with no project hours in the period.

    Empty when no timesheet has been uploaded for the period at all: with no data
    every employee would look idle, which is a gap in the data, not a bench.
    """
    start, end = resolve_period(db, date_from, date_to)
    empty = BenchList(
        date_from=start, date_to=end, total=0, page=page, page_size=page_size
    )
    # Any timesheet row at all in the period (across the whole company).
    anyone = _filters(start, end, None)
    if not db.scalar(select(func.count()).select_from(ProjectTimesheet).where(*anyone)):
        return empty

    logged = select(ProjectTimesheet.emp_id).where(*anyone)
    conditions = [
        Employee.emp_id.not_in(logged),
        func.lower(Employee.employment_status).not_in(EXITED_STATUSES),
    ]
    if scope is not None:
        conditions.append(Employee.emp_id.in_(scope))

    total = int(
        db.scalar(select(func.count()).select_from(Employee).where(*conditions)) or 0
    )
    employees = db.scalars(
        select(Employee)
        .where(*conditions)
        .order_by(Employee.employee_name, Employee.emp_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return BenchList(
        date_from=start,
        date_to=end,
        total=total,
        page=page,
        page_size=page_size,
        items=[
            BenchEmployeeRow(
                emp_id=employee.emp_id,
                employee_name=employee.employee_name,
                process=employee.process,
                designation=employee.designation,
                manager_name=employee.manager_name,
                tl_name=employee.tl_name,
            )
            for employee in employees
        ],
    )


def get_project_trends(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    scope: Select | None = None,
) -> ProjectTrends:
    """Total and billable hours for each day that has data."""
    start, end = resolve_period(db, date_from, date_to)
    rows = db.execute(
        select(
            ProjectTimesheet.report_date,
            func.coalesce(func.sum(ProjectTimesheet.hours), 0),
            _billable_hours(),
        )
        .where(*_filters(start, end, scope))
        .group_by(ProjectTimesheet.report_date)
        .order_by(ProjectTimesheet.report_date)
    ).all()

    return ProjectTrends(
        date_from=start,
        date_to=end,
        points=[
            ProjectTrendPoint(
                report_date=day, total_hours=_hours(total), billable_hours=_hours(billable)
            )
            for day, total, billable in rows
        ],
    )
