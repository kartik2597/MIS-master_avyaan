"""Hiring & attrition dashboard: who joined, who left, and the attrition rate.

Every function takes the same `scope` as the agent dashboard (a query of Employee
IDs, or None for no limit). A MANAGER or TL therefore sees the joiners and
leavers of their own team only, matched through the employee master. A joiner who
is not in the master yet is visible to ADMIN and MIS only.
"""

from datetime import date, timedelta

from sqlalchemy import Select, case, extract, func, or_, select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.employee_movement import EVENT_JOINED, EVENT_LEFT, EmployeeMovement
from app.schemas.hiring_dashboard import (
    ExitReasonCount,
    HiringEventList,
    HiringEventRow,
    HiringSummary,
    HiringTeamList,
    HiringTeamRow,
    HiringTrendPoint,
    HiringTrends,
)


# With no dates given, the dashboard covers this many days ending on the newest
# day that has a hiring or exit row.
DEFAULT_WINDOW_DAYS = 90
TOP_EXIT_REASONS = 5


def resolve_period(
    db: Session,
    date_from: date | None,
    date_to: date | None,
) -> tuple[date | None, date | None]:
    if date_from is None and date_to is None:
        latest = db.scalar(select(func.max(EmployeeMovement.report_date)))
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
        conditions.append(EmployeeMovement.report_date >= date_from)
    if date_to is not None:
        conditions.append(EmployeeMovement.report_date <= date_to)
    if scope is not None:
        conditions.append(EmployeeMovement.emp_id.in_(scope))
    return conditions


def _count_of(event_type: str):
    return func.coalesce(
        func.sum(case((EmployeeMovement.event_type == event_type, 1), else_=0)), 0
    )


def _opening_headcount(db: Session, date_from: date, scope: Select | None) -> int:
    """Employees on the master who had joined before the period and had not left yet."""
    left_before = select(EmployeeMovement.emp_id).where(
        EmployeeMovement.event_type == EVENT_LEFT,
        EmployeeMovement.report_date < date_from,
    )
    conditions = [
        Employee.date_of_joining < date_from,
        Employee.emp_id.not_in(left_before),
    ]
    if scope is not None:
        conditions.append(Employee.emp_id.in_(scope))
    return int(db.scalar(select(func.count()).select_from(Employee).where(*conditions)) or 0)


def get_hiring_summary(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    scope: Select | None = None,
) -> HiringSummary:
    start, end = resolve_period(db, date_from, date_to)
    filters = _filters(start, end, scope)
    row = db.execute(
        select(
            func.count(EmployeeMovement.id),
            _count_of(EVENT_JOINED),
            _count_of(EVENT_LEFT),
        ).where(*filters)
    ).one()
    rows_found = int(row[0] or 0)
    joiners = int(row[1] or 0)
    leavers = int(row[2] or 0)

    reasons = db.execute(
        select(EmployeeMovement.reason, func.count())
        .where(
            *filters,
            EmployeeMovement.event_type == EVENT_LEFT,
            EmployeeMovement.reason != "",
        )
        .group_by(EmployeeMovement.reason)
        .order_by(func.count().desc(), EmployeeMovement.reason)
        .limit(TOP_EXIT_REASONS)
    ).all()

    opening: int | None = None
    closing: int | None = None
    attrition: float | None = None
    if start is not None and rows_found:
        opening = _opening_headcount(db, start, scope)
        closing = max(opening + joiners - leavers, 0)
        average = (opening + closing) / 2
        if average > 0:
            attrition = round(leavers * 100 / average, 2)

    return HiringSummary(
        date_from=start,
        date_to=end,
        has_data=rows_found > 0,
        joiners=joiners,
        leavers=leavers,
        net_change=joiners - leavers,
        opening_headcount=opening,
        closing_headcount=closing,
        attrition_percent=attrition,
        top_exit_reasons=[
            ExitReasonCount(reason=reason, count=int(count)) for reason, count in reasons
        ],
    )


def _months_between(start: date, end: date) -> list[tuple[int, int]]:
    months: list[tuple[int, int]] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append((year, month))
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return months


def get_hiring_trends(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    scope: Select | None = None,
) -> HiringTrends:
    """Joiners and leavers per calendar month. Months with no events show 0."""
    start, end = resolve_period(db, date_from, date_to)
    year_of = extract("year", EmployeeMovement.report_date)
    month_of = extract("month", EmployeeMovement.report_date)
    rows = db.execute(
        select(
            year_of,
            month_of,
            _count_of(EVENT_JOINED),
            _count_of(EVENT_LEFT),
        )
        .where(*_filters(start, end, scope))
        .group_by(year_of, month_of)
    ).all()
    if not rows:
        return HiringTrends(date_from=start, date_to=end)

    by_month = {(int(year), int(month)): (int(j), int(l)) for year, month, j, l in rows}
    first = min(by_month) if start is None else (start.year, start.month)
    last = max(by_month) if end is None else (end.year, end.month)
    points = [
        HiringTrendPoint(
            month=f"{year:04d}-{month:02d}",
            joiners=by_month.get((year, month), (0, 0))[0],
            leavers=by_month.get((year, month), (0, 0))[1],
        )
        for year, month in _months_between(
            date(first[0], first[1], 1), date(last[0], last[1], 1)
        )
    ]
    return HiringTrends(date_from=start, date_to=end, points=points)


def get_hiring_teams(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    scope: Select | None = None,
) -> HiringTeamList:
    """Joiners and leavers per team, the team with most leavers first."""
    start, end = resolve_period(db, date_from, date_to)
    rows = db.execute(
        select(
            EmployeeMovement.team,
            _count_of(EVENT_JOINED),
            _count_of(EVENT_LEFT),
        )
        .where(*_filters(start, end, scope))
        .group_by(EmployeeMovement.team)
    ).all()

    items = [
        HiringTeamRow(team=team, joiners=int(j), leavers=int(l), net_change=int(j) - int(l))
        for team, j, l in rows
    ]
    items.sort(key=lambda item: (-item.leavers, -item.joiners, item.team))
    return HiringTeamList(date_from=start, date_to=end, items=items)


def get_hiring_events(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    event_type: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 10,
    scope: Select | None = None,
) -> HiringEventList:
    """Individual joiners and leavers, newest first, searchable by name or ID."""
    start, end = resolve_period(db, date_from, date_to)
    filters = _filters(start, end, scope)
    if event_type:
        filters.append(EmployeeMovement.event_type == event_type.upper())
    term = (search or "").strip()
    if term:
        pattern = f"%{term}%"
        filters.append(
            or_(
                EmployeeMovement.emp_id.ilike(pattern),
                EmployeeMovement.employee_name.ilike(pattern),
            )
        )

    total = int(
        db.scalar(select(func.count()).select_from(EmployeeMovement).where(*filters)) or 0
    )
    records = db.scalars(
        select(EmployeeMovement)
        .where(*filters)
        .order_by(
            EmployeeMovement.report_date.desc(),
            EmployeeMovement.employee_name,
            EmployeeMovement.emp_id,
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return HiringEventList(
        date_from=start,
        date_to=end,
        total=total,
        page=page,
        page_size=page_size,
        items=[
            HiringEventRow(
                emp_id=record.emp_id,
                employee_name=record.employee_name,
                event_type=record.event_type,
                event_date=record.report_date,
                team=record.team,
                designation=record.designation,
                manager_name=record.manager_name,
                detail=record.reason if record.event_type == EVENT_LEFT else record.hiring_source,
            )
            for record in records
        ],
    )
