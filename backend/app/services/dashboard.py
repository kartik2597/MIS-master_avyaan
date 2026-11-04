from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import Select, case, false, func, or_, select
from sqlalchemy.orm import Session

from app.models.agent_daily_performance import AgentDailyPerformance
from app.models.agent_shift_adherence import AgentShiftAdherence
from app.models.agent_shrinkage import AgentShrinkage
from app.models.employee import Employee
from app.models.user import User, UserRole
from app.reports.report_types import ReportType
from app.schemas.dashboard import (
    AttendanceBreakdown,
    AttendanceSlice,
    DashboardAgentList,
    DashboardAgentRow,
    DashboardFilterOptions,
    DashboardKpis,
    DashboardTrendPoint,
    DashboardTrends,
)


ZERO_DECIMAL = Decimal("0")
SECONDS_PER_HOUR = Decimal("3600")
TWO_PLACES = Decimal("0.01")

# The tables the KPI cards are built from. They must all describe the same day.
REPORT_MODELS = (AgentDailyPerformance, AgentShiftAdherence, AgentShrinkage)


def _decimal(value: object) -> Decimal:
    if value is None:
        return ZERO_DECIMAL
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _int(value: object) -> int:
    if value is None:
        return 0
    return int(value)


def _hours(seconds: object) -> Decimal:
    """Time columns are stored in seconds; the dashboard reports hours."""
    return (_decimal(seconds) / SECONDS_PER_HOUR).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )


def _percent(value: object) -> Decimal:
    return _decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _default_report_date(db: Session) -> date | None:
    """Pick the one day every card describes when no dates are given.

    Each report can be uploaded on a different day, so using each table's own
    latest date would make the cards describe different days. Instead take the
    newest day that every table with data has. If the tables share no day, use
    the newest day in any table; a table with nothing on that day then shows
    zeros rather than quietly showing another day.
    """
    day_sets = []
    for model in REPORT_MODELS:
        days = set(db.scalars(select(model.report_date).distinct()).all())
        if days:
            day_sets.append(days)

    if not day_sets:
        return None
    shared_days = set.intersection(*day_sets)
    if shared_days:
        return max(shared_days)
    return max(max(days) for days in day_sets)


def _date_filters(
    model,
    date_from: date | None,
    date_to: date | None,
    default_date: date | None,
) -> list:
    """Build the report_date filters for one table.

    With no dates given, the KPIs describe the single shared day chosen by
    _default_report_date, rather than adding up every day ever uploaded.
    """
    if date_from is None and date_to is None:
        if default_date is None:
            return []
        return [model.report_date == default_date]

    filters = []
    if date_from is not None:
        filters.append(model.report_date >= date_from)
    if date_to is not None:
        filters.append(model.report_date <= date_to)
    return filters


def get_dashboard_scope(db: Session, user: User) -> Select | None:
    """The employees a user may see on the dashboards, as a query of Employee IDs.

    - ADMIN and MIS see everyone (None means no limit).
    - MANAGER sees the employees whose manager_name is their own name.
    - TL sees the employees whose tl_name is their own name.

    A MANAGER or TL is matched through the Employee ID on their login. A user
    with no Employee ID, or one that is not in the employee master, sees
    nothing rather than everything.
    """
    if user.role in (UserRole.ADMIN, UserRole.MIS):
        return None

    me = None
    if user.emp_id:
        me = db.scalar(select(Employee).where(Employee.emp_id == user.emp_id))
    if me is None:
        return select(Employee.emp_id).where(false())

    team_column = (
        Employee.manager_name if user.role == UserRole.MANAGER else Employee.tl_name
    )
    return select(Employee.emp_id).where(
        func.lower(team_column) == me.employee_name.strip().lower()
    )


def apply_dashboard_filters(
    scope: Select | None,
    *,
    process: str | None = None,
    manager: str | None = None,
    tl: str | None = None,
    emp_id: str | None = None,
) -> Select | None:
    """Narrow the viewer's scope by the dashboard filter drop-downs.

    The result is still a query of Employee IDs, so every dashboard function
    keeps working unchanged. Filters are matched on the employee master and can
    only shrink what the viewer is already allowed to see, never widen it.
    """
    conditions = []
    for column, value in (
        (Employee.process, process),
        (Employee.manager_name, manager),
        (Employee.tl_name, tl),
        (Employee.emp_id, emp_id),
    ):
        text = (value or "").strip()
        if text:
            conditions.append(func.lower(column) == text.lower())
    if not conditions:
        return scope

    narrowed = select(Employee.emp_id).where(*conditions)
    if scope is not None:
        narrowed = narrowed.where(Employee.emp_id.in_(scope))
    return narrowed


def get_dashboard_filter_options(
    db: Session,
    scope: Select | None = None,
) -> DashboardFilterOptions:
    """Process, manager and TL names the drop-downs can offer to this viewer."""

    def distinct_values(column) -> list[str]:
        statement = select(column).distinct().order_by(column)
        if scope is not None:
            statement = statement.where(Employee.emp_id.in_(scope))
        return [value for value in db.scalars(statement).all() if value and value.strip()]

    return DashboardFilterOptions(
        processes=distinct_values(Employee.process),
        managers=distinct_values(Employee.manager_name),
        tls=distinct_values(Employee.tl_name),
    )


def _scope_filters(model, scope: Select | None) -> list:
    """Limit one table to the employees in the scope. No scope, no filter."""
    if scope is None:
        return []
    return [model.emp_id.in_(scope)]


def _has_rows(db: Session, model, filters: list) -> bool:
    """True when the table has at least one row for the chosen day or range."""
    count = db.scalar(select(func.count()).select_from(model).where(*filters))
    return bool(count)


def get_dashboard_kpis(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    scope: Select | None = None,
) -> DashboardKpis:
    """Roll up the KPI cards.

    - With no dates given, every card describes the same single day.
    - Time totals are summed over the period and returned in hours.
    - Login time comes from the shift adherence report ("Login hours"); staff,
      talk, idle and break time come from the APR report.
    - Late/early/adherence/attrition counts are summed over the period.
    - Head count and present count are the average per day in the period.
    - Shrinkage is a percentage, so it is averaged, not summed.
    """
    default_date = (
        _default_report_date(db) if date_from is None and date_to is None else None
    )
    performance_filters = _date_filters(
        AgentDailyPerformance, date_from, date_to, default_date
    )
    adherence_filters = _date_filters(
        AgentShiftAdherence, date_from, date_to, default_date
    )
    shrinkage_filters = _date_filters(AgentShrinkage, date_from, date_to, default_date)
    performance_filters += _scope_filters(AgentDailyPerformance, scope)
    adherence_filters += _scope_filters(AgentShiftAdherence, scope)
    shrinkage_filters += _scope_filters(AgentShrinkage, scope)

    performance_totals = db.execute(
        select(
            func.coalesce(func.sum(AgentDailyPerformance.talk_time), 0),
            func.coalesce(func.sum(AgentDailyPerformance.staff_time), 0),
            func.coalesce(func.sum(AgentDailyPerformance.idle_time), 0),
            func.coalesce(func.sum(AgentDailyPerformance.break_time), 0),
        ).where(*performance_filters)
    ).one()

    adherence_totals = db.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (AgentShiftAdherence.late_login_minutes > 0, 1),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (AgentShiftAdherence.early_logout_minutes > 0, 1),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (AgentShiftAdherence.adherence_flag.is_(True), 1),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (AgentShiftAdherence.non_adherence_flag.is_(True), 1),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(func.sum(AgentShiftAdherence.downtime_seconds), 0),
            func.coalesce(func.sum(AgentShiftAdherence.login_hours_seconds), 0),
        ).where(*adherence_filters)
    ).one()

    shrinkage_totals = db.execute(
        select(
            func.coalesce(func.sum(AgentShrinkage.agent_count), 0),
            func.coalesce(func.sum(AgentShrinkage.present_count), 0),
            func.coalesce(func.avg(AgentShrinkage.planned_shrinkage), 0),
            func.coalesce(func.avg(AgentShrinkage.unplanned_shrinkage), 0),
            func.coalesce(func.sum(AgentShrinkage.attrition), 0),
            func.count(func.distinct(AgentShrinkage.report_date)),
        ).where(*shrinkage_filters)
    ).one()

    days_with_data = max(_int(shrinkage_totals[5]), 1)
    planned_shrinkage = _percent(shrinkage_totals[2])
    unplanned_shrinkage = _percent(shrinkage_totals[3])

    # A report with no rows has no real numbers: the zeros above are just the
    # COALESCE fallback. Tell the UI so it can show "No data" for those cards.
    missing_reports = [
        report_type.value
        for report_type, model, filters in (
            (ReportType.APR, AgentDailyPerformance, performance_filters),
            (ReportType.SHIFT_ADHERENCE, AgentShiftAdherence, adherence_filters),
            (ReportType.SHRINKAGE, AgentShrinkage, shrinkage_filters),
        )
        if not _has_rows(db, model, filters)
    ]

    return DashboardKpis(
        head_count=round(_int(shrinkage_totals[0]) / days_with_data),
        present_count=round(_int(shrinkage_totals[1]) / days_with_data),
        late_login_count=_int(adherence_totals[0]),
        early_logout_count=_int(adherence_totals[1]),
        shift_adherence_count=_int(adherence_totals[2]),
        non_adherence_count=_int(adherence_totals[3]),
        planned_shrinkage=planned_shrinkage,
        unplanned_shrinkage=unplanned_shrinkage,
        overall_shrinkage=planned_shrinkage + unplanned_shrinkage,
        attrition_count=_int(shrinkage_totals[4]),
        total_talk_time=_hours(performance_totals[0]),
        total_login_time=_hours(adherence_totals[5]),
        total_staff_time=_hours(performance_totals[1]),
        total_downtime=_hours(adherence_totals[4]),
        total_idle_time=_hours(performance_totals[2]),
        total_break_time=_hours(performance_totals[3]),
        report_date=default_date,
        missing_reports=missing_reports,
    )


# --- Trends, attendance breakdown and the agent table -------------------------

# With no dates given the trend charts show this many days, ending on the newest
# day that any report has.
TREND_DEFAULT_DAYS = 30

# Attendance values seen in the reports, folded into a few readable groups.
PRESENT_VALUES = ("present", "p")
ATTENDANCE_GROUPS = {
    "present": "Present",
    "p": "Present",
    "absent": "Absent",
    "a": "Absent",
    "leave": "Leave",
    "cl": "Leave",
    "lwp": "LWP",
    "half day": "Half Day",
    "half-day": "Half Day",
    "hd": "Half Day",
    "training": "Training",
    "tp": "Training",
}
ATTENDANCE_ORDER = ["Present", "Absent", "Leave", "LWP", "Half Day", "Training", "Other"]


def _attendance_label(raw: object) -> str:
    return ATTENDANCE_GROUPS.get(str(raw or "").strip().lower(), "Other")


def _present_case():
    """1 for a row whose attendance means present, else 0 (for SUM)."""
    return case(
        (func.lower(AgentDailyPerformance.attendance).in_(PRESENT_VALUES), 1),
        else_=0,
    )


def _latest_report_date(db: Session) -> date | None:
    days = [db.scalar(select(func.max(model.report_date))) for model in REPORT_MODELS]
    days = [day for day in days if day is not None]
    return max(days) if days else None


def _trend_window(
    db: Session,
    date_from: date | None,
    date_to: date | None,
) -> tuple[date | None, date | None]:
    if date_from is None and date_to is None:
        latest = _latest_report_date(db)
        if latest is None:
            return None, None
        return latest - timedelta(days=TREND_DEFAULT_DAYS - 1), latest
    return date_from, date_to


def get_dashboard_trends(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    scope: Select | None = None,
) -> DashboardTrends:
    """One point per day: head count, present, adherence %, shrinkage %, times.

    Head count and present come from the shrinkage report; when a day has no
    shrinkage rows they fall back to the daily activity (APR) rows so the chart
    is not empty just because one report is missing.
    """
    start, end = _trend_window(db, date_from, date_to)
    performance_filters = _date_filters(AgentDailyPerformance, start, end, None)
    adherence_filters = _date_filters(AgentShiftAdherence, start, end, None)
    shrinkage_filters = _date_filters(AgentShrinkage, start, end, None)
    performance_filters += _scope_filters(AgentDailyPerformance, scope)
    adherence_filters += _scope_filters(AgentShiftAdherence, scope)
    shrinkage_filters += _scope_filters(AgentShrinkage, scope)

    shrinkage_by_day = {
        row[0]: row
        for row in db.execute(
            select(
                AgentShrinkage.report_date,
                func.coalesce(func.sum(AgentShrinkage.agent_count), 0),
                func.coalesce(func.sum(AgentShrinkage.present_count), 0),
                func.coalesce(func.avg(AgentShrinkage.planned_shrinkage), 0),
                func.coalesce(func.avg(AgentShrinkage.unplanned_shrinkage), 0),
            )
            .where(*shrinkage_filters)
            .group_by(AgentShrinkage.report_date)
        ).all()
    }
    adherence_by_day = {
        row[0]: row
        for row in db.execute(
            select(
                AgentShiftAdherence.report_date,
                func.coalesce(
                    func.sum(case((AgentShiftAdherence.adherence_flag.is_(True), 1), else_=0)),
                    0,
                ),
                func.coalesce(
                    func.sum(case((AgentShiftAdherence.non_adherence_flag.is_(True), 1), else_=0)),
                    0,
                ),
            )
            .where(*adherence_filters)
            .group_by(AgentShiftAdherence.report_date)
        ).all()
    }
    performance_by_day = {
        row[0]: row
        for row in db.execute(
            select(
                AgentDailyPerformance.report_date,
                func.coalesce(func.sum(AgentDailyPerformance.talk_time), 0),
                func.coalesce(func.sum(AgentDailyPerformance.staff_time), 0),
                func.count(AgentDailyPerformance.id),
                func.coalesce(func.sum(_present_case()), 0),
            )
            .where(*performance_filters)
            .group_by(AgentDailyPerformance.report_date)
        ).all()
    }

    days = sorted({*shrinkage_by_day, *adherence_by_day, *performance_by_day})
    points: list[DashboardTrendPoint] = []
    for day in days:
        shrinkage_row = shrinkage_by_day.get(day)
        adherence_row = adherence_by_day.get(day)
        performance_row = performance_by_day.get(day)

        adherent = _int(adherence_row[1]) if adherence_row else 0
        not_adherent = _int(adherence_row[2]) if adherence_row else 0
        checked = adherent + not_adherent

        if shrinkage_row is not None:
            head_count = _int(shrinkage_row[1])
            present_count = _int(shrinkage_row[2])
        elif performance_row is not None:
            head_count = _int(performance_row[3])
            present_count = _int(performance_row[4])
        else:
            head_count = present_count = 0

        points.append(
            DashboardTrendPoint(
                report_date=day,
                head_count=head_count,
                present_count=present_count,
                adherence_percent=round(adherent * 100 / checked, 2) if checked else None,
                overall_shrinkage=(
                    float(_percent(shrinkage_row[3]) + _percent(shrinkage_row[4]))
                    if shrinkage_row is not None
                    else None
                ),
                talk_time=float(_hours(performance_row[1])) if performance_row else 0.0,
                staff_time=float(_hours(performance_row[2])) if performance_row else 0.0,
            )
        )
    return DashboardTrends(points=points)


def get_dashboard_attendance(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    scope: Select | None = None,
) -> AttendanceBreakdown:
    """How many agent-days were Present / Absent / Leave / ... for the period.

    Counts come from the daily activity rows, which hold every agent every day
    (including the ones who were absent or on leave).
    """
    default_date = (
        _default_report_date(db) if date_from is None and date_to is None else None
    )
    filters = _date_filters(AgentDailyPerformance, date_from, date_to, default_date)
    filters += _scope_filters(AgentDailyPerformance, scope)
    rows = db.execute(
        select(AgentDailyPerformance.attendance, func.count())
        .where(*filters)
        .group_by(AgentDailyPerformance.attendance)
    ).all()

    counts: dict[str, int] = {}
    for raw_status, count in rows:
        label = _attendance_label(raw_status)
        counts[label] = counts.get(label, 0) + _int(count)

    slices = [
        AttendanceSlice(status=label, count=counts[label])
        for label in ATTENDANCE_ORDER
        if counts.get(label)
    ]
    return AttendanceBreakdown(
        slices=slices,
        total=sum(item.count for item in slices),
        report_date=default_date,
    )


def get_dashboard_agents(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 10,
    scope: Select | None = None,
) -> DashboardAgentList:
    """One row per agent for the period, searchable by employee id or name.

    Activity times (talk, idle, break) come from the daily activity rows; login
    hours and the late / early / adherent counts come from shift adherence, the
    same sources the KPI cards use.
    """
    default_date = (
        _default_report_date(db) if date_from is None and date_to is None else None
    )
    performance_filters = _date_filters(
        AgentDailyPerformance, date_from, date_to, default_date
    )
    adherence_filters = _date_filters(
        AgentShiftAdherence, date_from, date_to, default_date
    )
    performance_filters += _scope_filters(AgentDailyPerformance, scope)
    adherence_filters += _scope_filters(AgentShiftAdherence, scope)
    term = (search or "").strip()
    if term:
        pattern = f"%{term}%"
        performance_filters.append(
            or_(
                AgentDailyPerformance.emp_id.ilike(pattern),
                AgentDailyPerformance.employee_name.ilike(pattern),
            )
        )

    per_agent = (
        select(
            AgentDailyPerformance.emp_id.label("emp_id"),
            func.max(AgentDailyPerformance.employee_name).label("employee_name"),
            func.max(AgentDailyPerformance.campaign).label("process"),
            func.count(AgentDailyPerformance.id).label("days_recorded"),
            func.coalesce(func.sum(_present_case()), 0).label("days_present"),
            func.coalesce(func.sum(AgentDailyPerformance.talk_time), 0).label("talk"),
            func.coalesce(func.sum(AgentDailyPerformance.idle_time), 0).label("idle"),
            func.coalesce(func.sum(AgentDailyPerformance.break_time), 0).label("brk"),
        )
        .where(*performance_filters)
        .group_by(AgentDailyPerformance.emp_id)
    )
    total = _int(db.scalar(select(func.count()).select_from(per_agent.subquery())))
    agent_rows = db.execute(
        per_agent.order_by(
            func.max(AgentDailyPerformance.employee_name),
            AgentDailyPerformance.emp_id,
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    adherence_by_agent: dict[str, object] = {}
    emp_ids = [row.emp_id for row in agent_rows]
    if emp_ids:
        adherence_by_agent = {
            row[0]: row
            for row in db.execute(
                select(
                    AgentShiftAdherence.emp_id,
                    func.coalesce(
                        func.sum(case((AgentShiftAdherence.late_login_minutes > 0, 1), else_=0)),
                        0,
                    ),
                    func.coalesce(
                        func.sum(case((AgentShiftAdherence.early_logout_minutes > 0, 1), else_=0)),
                        0,
                    ),
                    func.coalesce(
                        func.sum(case((AgentShiftAdherence.adherence_flag.is_(True), 1), else_=0)),
                        0,
                    ),
                    func.coalesce(func.sum(AgentShiftAdherence.login_hours_seconds), 0),
                )
                .where(*adherence_filters, AgentShiftAdherence.emp_id.in_(emp_ids))
                .group_by(AgentShiftAdherence.emp_id)
            ).all()
        }

    items: list[DashboardAgentRow] = []
    for row in agent_rows:
        adherence_row = adherence_by_agent.get(row.emp_id)
        items.append(
            DashboardAgentRow(
                emp_id=row.emp_id,
                employee_name=row.employee_name,
                process=row.process,
                days_recorded=_int(row.days_recorded),
                days_present=_int(row.days_present),
                login_hours=float(_hours(adherence_row[4])) if adherence_row else 0.0,
                talk_time=float(_hours(row.talk)),
                idle_time=float(_hours(row.idle)),
                break_time=float(_hours(row.brk)),
                late_logins=_int(adherence_row[1]) if adherence_row else 0,
                early_logouts=_int(adherence_row[2]) if adherence_row else 0,
                adherent_days=_int(adherence_row[3]) if adherence_row else 0,
            )
        )
    return DashboardAgentList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        report_date=default_date,
    )
