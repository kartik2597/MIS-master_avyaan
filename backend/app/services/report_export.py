"""Daily, weekly and monthly MIS reports as Excel and PDF files.

The numbers come from the same functions the dashboards use, so an exported report
always agrees with what the dashboards show for the same dates and team.

A report holds up to three sections, picked with `sections`:
  agent    agent performance (get_dashboard_kpis / trends / agents)
  project  projects and timesheets (get_project_*)
  hiring   hiring and attrition (get_hiring_*)
  uploads  upload and data quality: failed uploads, skipped rows, days with no upload
           (all-teams view only, because uploads do not belong to a team)
  utilization  how fully each person's time is used (logged hours vs working-day capacity)
"""

import logging
import smtplib
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path
from typing import Iterable, Literal

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.upload_history import UploadHistory
from app.schemas.dashboard import DashboardAgentRow, DashboardKpis, DashboardTrends
from app.schemas.hiring_dashboard import (
    HiringEventRow,
    HiringSummary,
    HiringTeamRow,
    HiringTrendPoint,
)
from app.schemas.project_dashboard import (
    BenchEmployeeRow,
    ProjectEmployeeRow,
    ProjectHoursRow,
    ProjectSummary,
    ProjectTrendPoint,
)
from app.services.dashboard import (
    get_dashboard_agents,
    get_dashboard_kpis,
    get_dashboard_trends,
)
from app.services.upload_history import FAILED_STATUSES
from app.services.hiring_dashboard import (
    get_hiring_events,
    get_hiring_summary,
    get_hiring_teams,
    get_hiring_trends,
)
from app.services.project_dashboard import (
    get_bench,
    get_project_employees,
    get_project_hours,
    get_project_summary,
    get_project_trends,
)


logger = logging.getLogger(__name__)

ReportKind = Literal["daily", "weekly", "monthly"]
ReportFormat = Literal["xlsx", "pdf"]
ReportSection = Literal["agent", "project", "hiring", "uploads", "utilization"]

REPORT_KINDS: tuple[str, ...] = ("daily", "weekly", "monthly")
REPORT_SECTIONS: tuple[str, ...] = ("agent", "project", "hiring", "uploads", "utilization")

# Utilization is logged hours against this many hours per working day (Monday to Friday).
# There is no holiday or leave calendar, so those days still count as working days.
STANDARD_DAILY_HOURS = 8.0
UNDER_UTILIZED_BELOW = 50.0
OVER_UTILIZED_ABOVE = 110.0
# The PDF lists at most this many rows per table; the Excel file always has all of them.
PDF_MAX_ROWS = 200
PDF_MAX_AGENTS = PDF_MAX_ROWS  # older name, kept so existing imports keep working

# The services page their results; a report wants every row.
ALL_ROWS = 1_000_000


@dataclass
class ProjectReport:
    summary: ProjectSummary
    projects: list[ProjectHoursRow]
    employees: list[ProjectEmployeeRow]
    bench: list[BenchEmployeeRow]
    trends: list[ProjectTrendPoint]


@dataclass
class HiringReport:
    summary: HiringSummary
    trends: list[HiringTrendPoint]
    teams: list[HiringTeamRow]
    events: list[HiringEventRow]


@dataclass
class UploadTypeRow:
    report_type: str
    uploads: int
    completed: int
    failed: int
    rows_processed: int
    rows_skipped: int


@dataclass
class UploadIssueRow:
    uploaded_at: datetime
    file_name: str
    report_type: str
    status: str
    uploaded_by: str | None
    rows_skipped: int
    message: str | None


@dataclass
class UploadsReport:
    total: int
    completed: int
    failed: int
    with_skipped_rows: int
    rows_processed: int
    rows_skipped: int
    by_type: list[UploadTypeRow]
    issues: list[UploadIssueRow]
    days_without_upload: list[date]

    @property
    def has_data(self) -> bool:
        return self.total > 0


@dataclass
class UtilizationRow:
    emp_id: str
    employee_name: str
    total_hours: float
    billable_hours: float
    capacity_hours: float
    utilization_percent: float | None
    billable_utilization_percent: float | None
    status: str


@dataclass
class UtilizationReport:
    working_days: int
    capacity_per_person: float
    people: int
    avg_utilization_percent: float | None
    avg_billable_utilization_percent: float | None
    under_utilized: int
    over_utilized: int
    on_bench: int
    rows: list[UtilizationRow]


@dataclass
class ReportData:
    kind: str
    date_from: date
    date_to: date
    generated_at: datetime
    kpis: DashboardKpis | None = None
    trends: DashboardTrends | None = None
    agents: list[DashboardAgentRow] = field(default_factory=list)
    projects: ProjectReport | None = None
    hiring: HiringReport | None = None
    uploads: UploadsReport | None = None
    utilization: UtilizationReport | None = None

    @property
    def title(self) -> str:
        return f"{self.kind.capitalize()} MIS report"

    @property
    def period_text(self) -> str:
        if self.date_from == self.date_to:
            return self.date_from.isoformat()
        return f"{self.date_from.isoformat()} to {self.date_to.isoformat()}"

    @property
    def file_stem(self) -> str:
        return f"{self.kind}_{self.date_from.isoformat()}_{self.date_to.isoformat()}"


def period_for(kind: str, today: date) -> tuple[date, date]:
    """The finished period a scheduled report covers.

    daily   -> yesterday
    weekly  -> the previous Monday to Sunday
    monthly -> the previous calendar month
    """
    if kind == "daily":
        day = today - timedelta(days=1)
        return day, day
    if kind == "weekly":
        this_monday = today - timedelta(days=today.weekday())
        start = this_monday - timedelta(days=7)
        return start, start + timedelta(days=6)
    if kind == "monthly":
        end = today.replace(day=1) - timedelta(days=1)
        return end.replace(day=1), end
    raise ValueError(f"Unknown report kind: {kind}")


def _build_project_report(
    db: Session, date_from: date, date_to: date, scope: Select | None
) -> ProjectReport:
    return ProjectReport(
        summary=get_project_summary(db, date_from=date_from, date_to=date_to, scope=scope),
        projects=get_project_hours(
            db, date_from=date_from, date_to=date_to, scope=scope, limit=ALL_ROWS
        ).items,
        employees=get_project_employees(
            db, date_from=date_from, date_to=date_to, page=1, page_size=ALL_ROWS, scope=scope
        ).items,
        bench=get_bench(
            db, date_from=date_from, date_to=date_to, page=1, page_size=ALL_ROWS, scope=scope
        ).items,
        trends=get_project_trends(db, date_from=date_from, date_to=date_to, scope=scope).points,
    )


def _build_hiring_report(
    db: Session, date_from: date, date_to: date, scope: Select | None
) -> HiringReport:
    return HiringReport(
        summary=get_hiring_summary(db, date_from=date_from, date_to=date_to, scope=scope),
        trends=get_hiring_trends(db, date_from=date_from, date_to=date_to, scope=scope).points,
        teams=get_hiring_teams(db, date_from=date_from, date_to=date_to, scope=scope).items,
        events=get_hiring_events(
            db, date_from=date_from, date_to=date_to, page=1, page_size=ALL_ROWS, scope=scope
        ).items,
    )


# A calendar with more days than this is not worth listing day by day.
MAX_DAYS_CHECKED_FOR_UPLOADS = 366


def _build_uploads_report(db: Session, date_from: date, date_to: date) -> UploadsReport:
    """Upload health for the period, by the day each file was uploaded."""
    uploaded_day = func.date(UploadHistory.uploaded_at)
    uploads = db.scalars(
        select(UploadHistory)
        .options(selectinload(UploadHistory.uploader))
        .where(uploaded_day >= date_from, uploaded_day <= date_to)
        .order_by(UploadHistory.uploaded_at)
    ).all()

    by_type: dict[str, UploadTypeRow] = {}
    issues: list[UploadIssueRow] = []
    days_with_upload: set[date] = set()
    completed = failed = with_skipped_rows = rows_processed = rows_skipped = 0

    for upload in uploads:
        days_with_upload.add(upload.uploaded_at.date())
        row = by_type.setdefault(
            upload.report_type, UploadTypeRow(upload.report_type, 0, 0, 0, 0, 0)
        )
        row.uploads += 1
        row.rows_processed += upload.processed_records or 0
        row.rows_skipped += upload.failed_records or 0
        rows_processed += upload.processed_records or 0
        rows_skipped += upload.failed_records or 0

        is_failed = upload.upload_status in FAILED_STATUSES
        if upload.upload_status == "COMPLETED":
            completed += 1
            row.completed += 1
        if is_failed:
            failed += 1
            row.failed += 1
        if (upload.failed_records or 0) > 0:
            with_skipped_rows += 1
        if is_failed or (upload.failed_records or 0) > 0:
            issues.append(
                UploadIssueRow(
                    uploaded_at=upload.uploaded_at,
                    file_name=upload.original_file_name,
                    report_type=upload.report_type,
                    status=upload.upload_status,
                    uploaded_by=upload.uploaded_by_name,
                    rows_skipped=upload.failed_records or 0,
                    message=upload.error_message,
                )
            )

    missing_days: list[date] = []
    span = (date_to - date_from).days + 1
    if 0 < span <= MAX_DAYS_CHECKED_FOR_UPLOADS:
        missing_days = [
            date_from + timedelta(days=offset)
            for offset in range(span)
            if (date_from + timedelta(days=offset)) not in days_with_upload
        ]

    return UploadsReport(
        total=len(uploads),
        completed=completed,
        failed=failed,
        with_skipped_rows=with_skipped_rows,
        rows_processed=rows_processed,
        rows_skipped=rows_skipped,
        by_type=sorted(by_type.values(), key=lambda item: item.report_type),
        issues=issues,
        days_without_upload=missing_days,
    )


def _working_days(date_from: date, date_to: date) -> int:
    """Monday to Friday days in the period, both ends included."""
    days = (date_to - date_from).days + 1
    return sum(1 for offset in range(max(days, 0)) if (date_from + timedelta(days=offset)).weekday() < 5)


def _utilization_status(total_hours: float, percent: float | None) -> str:
    if total_hours <= 0:
        return "Bench"
    if percent is None:
        return "-"
    if percent < UNDER_UTILIZED_BELOW:
        return "Under-utilized"
    if percent > OVER_UTILIZED_ABOVE:
        return "Over-utilized"
    return "On target"


def _build_utilization_report(
    projects: ProjectReport, date_from: date, date_to: date
) -> UtilizationReport:
    """Logged hours against working-day capacity, for everyone who logged time or is on the bench."""
    working_days = _working_days(date_from, date_to)
    capacity = working_days * STANDARD_DAILY_HOURS

    def percent(part: float) -> float | None:
        return round(part * 100 / capacity, 2) if capacity > 0 else None

    rows: list[UtilizationRow] = []
    for employee in projects.employees:
        utilization = percent(employee.total_hours)
        rows.append(
            UtilizationRow(
                emp_id=employee.emp_id,
                employee_name=employee.employee_name,
                total_hours=employee.total_hours,
                billable_hours=employee.billable_hours,
                capacity_hours=capacity,
                utilization_percent=utilization,
                billable_utilization_percent=percent(employee.billable_hours),
                status=_utilization_status(employee.total_hours, utilization),
            )
        )
    for bench in projects.bench:
        rows.append(
            UtilizationRow(
                emp_id=bench.emp_id,
                employee_name=bench.employee_name,
                total_hours=0.0,
                billable_hours=0.0,
                capacity_hours=capacity,
                utilization_percent=0.0 if capacity > 0 else None,
                billable_utilization_percent=0.0 if capacity > 0 else None,
                status="Bench",
            )
        )
    # Lowest use first, so the people who need attention are at the top.
    rows.sort(key=lambda row: (row.utilization_percent is None, row.utilization_percent or 0))

    people = len(rows)
    total_capacity = capacity * people
    total_hours = sum(row.total_hours for row in rows)
    billable_hours = sum(row.billable_hours for row in rows)
    return UtilizationReport(
        working_days=working_days,
        capacity_per_person=capacity,
        people=people,
        avg_utilization_percent=(
            round(total_hours * 100 / total_capacity, 2) if total_capacity > 0 else None
        ),
        avg_billable_utilization_percent=(
            round(billable_hours * 100 / total_capacity, 2) if total_capacity > 0 else None
        ),
        under_utilized=sum(1 for row in rows if row.status == "Under-utilized"),
        over_utilized=sum(1 for row in rows if row.status == "Over-utilized"),
        on_bench=sum(1 for row in rows if row.status == "Bench"),
        rows=rows,
    )


def build_report_data(
    db: Session,
    kind: str,
    date_from: date,
    date_to: date,
    scope: Select | None = None,
    sections: Iterable[str] = REPORT_SECTIONS,
) -> ReportData:
    wanted = set(sections)
    unknown = wanted - set(REPORT_SECTIONS)
    if unknown:
        raise ValueError(f"Unknown report section: {', '.join(sorted(unknown))}")
    if not wanted:
        raise ValueError("Pick at least one report section.")

    data = ReportData(
        kind=kind, date_from=date_from, date_to=date_to, generated_at=datetime.now()
    )
    if "agent" in wanted:
        data.kpis = get_dashboard_kpis(db, date_from=date_from, date_to=date_to, scope=scope)
        data.trends = get_dashboard_trends(db, date_from=date_from, date_to=date_to, scope=scope)
        data.agents = get_dashboard_agents(
            db,
            date_from=date_from,
            date_to=date_to,
            page=1,
            page_size=ALL_ROWS,
            scope=scope,
        ).items
    if "project" in wanted:
        data.projects = _build_project_report(db, date_from, date_to, scope)
    if "hiring" in wanted:
        data.hiring = _build_hiring_report(db, date_from, date_to, scope)
    # Uploads are not tied to a team, so a team-scoped (MANAGER / TL) report leaves
    # this section out instead of showing other people's files.
    if "uploads" in wanted and scope is None:
        data.uploads = _build_uploads_report(db, date_from, date_to)
    if "utilization" in wanted:
        # Same people and hours as the project section, so the two always agree.
        source = data.projects or _build_project_report(db, date_from, date_to, scope)
        data.utilization = _build_utilization_report(source, date_from, date_to)
        data.utilization_has_hours = source.summary.has_data
    return data


def _percent_of(part: float, whole: float) -> str:
    return f"{part * 100 / whole:.2f}%" if whole > 0 else "-"


def _percent_or_dash(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}%"


def kpi_rows(kpis: DashboardKpis) -> list[tuple[str, str]]:
    """Label / value pairs for the summary, in the order the dashboard shows them."""
    adherence_total = kpis.shift_adherence_count + kpis.non_adherence_count
    return [
        ("Head count (avg per day)", str(kpis.head_count)),
        ("Present (avg per day)", str(kpis.present_count)),
        ("Attendance %", _percent_of(kpis.present_count, kpis.head_count)),
        ("Shift adherence %", _percent_of(kpis.shift_adherence_count, adherence_total)),
        ("Planned shrinkage %", f"{kpis.planned_shrinkage}"),
        ("Unplanned shrinkage %", f"{kpis.unplanned_shrinkage}"),
        ("Overall shrinkage %", f"{kpis.overall_shrinkage}"),
        ("Attrition", str(kpis.attrition_count)),
        ("Late logins", str(kpis.late_login_count)),
        ("Early logouts", str(kpis.early_logout_count)),
        ("Shift adherence (count)", str(kpis.shift_adherence_count)),
        ("Non adherence (count)", str(kpis.non_adherence_count)),
        ("Login hours", f"{kpis.total_login_time}"),
        ("Staff hours", f"{kpis.total_staff_time}"),
        ("Talk hours", f"{kpis.total_talk_time}"),
        ("Idle hours", f"{kpis.total_idle_time}"),
        ("Break hours", f"{kpis.total_break_time}"),
        ("Downtime hours", f"{kpis.total_downtime}"),
    ]


def project_kpi_rows(summary: ProjectSummary) -> list[tuple[str, str]]:
    return [
        ("Total hours", f"{summary.total_hours:.2f}"),
        ("Billable hours", f"{summary.billable_hours:.2f}"),
        ("Non-billable hours", f"{summary.non_billable_hours:.2f}"),
        ("Billable %", _percent_or_dash(summary.billable_percent)),
        ("Employees who logged hours", str(summary.employees_logged)),
        ("Active projects", str(summary.active_projects)),
        ("Avg hours per employee", f"{summary.avg_hours_per_employee:.2f}"),
    ]


def hiring_kpi_rows(summary: HiringSummary) -> list[tuple[str, str]]:
    def count(value: int | None) -> str:
        return "-" if value is None else str(value)

    net = f"+{summary.net_change}" if summary.net_change > 0 else str(summary.net_change)
    rows = [
        ("Joiners", str(summary.joiners)),
        ("Leavers", str(summary.leavers)),
        ("Net change", net),
        ("Opening headcount", count(summary.opening_headcount)),
        ("Closing headcount", count(summary.closing_headcount)),
        ("Attrition %", _percent_or_dash(summary.attrition_percent)),
    ]
    rows += [(f"Exit reason: {item.reason}", str(item.count)) for item in summary.top_exit_reasons]
    return rows


def uploads_kpi_rows(report: UploadsReport) -> list[tuple[str, str]]:
    return [
        ("Files uploaded", str(report.total)),
        ("Completed", str(report.completed)),
        ("Failed", str(report.failed)),
        ("Imported with skipped rows", str(report.with_skipped_rows)),
        ("Rows imported", str(report.rows_processed)),
        ("Rows skipped", str(report.rows_skipped)),
        ("Days with no upload", str(len(report.days_without_upload))),
    ]


def utilization_kpi_rows(report: UtilizationReport) -> list[tuple[str, str]]:
    return [
        ("Working days (Mon-Fri)", str(report.working_days)),
        ("Capacity per person (hrs)", f"{report.capacity_per_person:.1f}"),
        ("People counted", str(report.people)),
        ("Average utilization %", _percent_or_dash(report.avg_utilization_percent)),
        ("Average billable utilization %", _percent_or_dash(report.avg_billable_utilization_percent)),
        (f"Under-utilized (below {UNDER_UTILIZED_BELOW:.0f}%)", str(report.under_utilized)),
        (f"Over-utilized (above {OVER_UTILIZED_ABOVE:.0f}%)", str(report.over_utilized)),
        ("On bench (no hours)", str(report.on_bench)),
    ]


def summary_blocks(data: ReportData) -> list[tuple[str, list[tuple[str, str]]]]:
    """The summary figures of each section in the report, as (heading, rows)."""
    blocks: list[tuple[str, list[tuple[str, str]]]] = []
    if data.kpis is not None:
        blocks.append(("Agent performance", kpi_rows(data.kpis)))
    if data.projects is not None:
        blocks.append(("Projects and timesheets", project_kpi_rows(data.projects.summary)))
    if data.hiring is not None:
        blocks.append(("Hiring and attrition", hiring_kpi_rows(data.hiring.summary)))
    if data.uploads is not None:
        blocks.append(("Uploads and data quality", uploads_kpi_rows(data.uploads)))
    if data.utilization is not None:
        blocks.append(("Resource utilization", utilization_kpi_rows(data.utilization)))
    return blocks


def missing_notes(data: ReportData) -> list[str]:
    """Plain-language warnings for sections that had no uploaded data."""
    notes: list[str] = []
    if data.kpis is not None and data.kpis.missing_reports:
        notes.append(
            "No data uploaded for: " + ", ".join(data.kpis.missing_reports) + ". Related figures show 0."
        )
    if data.projects is not None and not data.projects.summary.has_data:
        notes.append("No project timesheet data for this period. Project figures show 0.")
    if data.hiring is not None and not data.hiring.summary.has_data:
        notes.append("No hiring or attrition data for this period. Hiring figures show 0.")
    if data.utilization is not None and not data.utilization_has_hours:
        notes.append(
            "No project timesheet data for this period. Everyone shows as bench in the utilization figures."
        )
    if data.uploads is not None and data.uploads.failed:
        notes.append(
            f"{data.uploads.failed} upload(s) failed in this period. See the Upload issues table."
        )
    return notes


# --- Tables shared by Excel and PDF --------------------------------------------
# Each table is (sheet title, headers, rows). The Excel file writes every table; the
# PDF writes the same ones, trimmed to PDF_MAX_ROWS.


def _agent_tables(data: ReportData) -> list[tuple[str, list[str], list[list]]]:
    if data.kpis is None or data.trends is None:
        return []
    return [
        (
            "Daily trend",
            ["Date", "Head count", "Present", "Adherence %", "Shrinkage %", "Talk hrs", "Staff hrs"],
            [
                [
                    p.report_date, p.head_count, p.present_count, p.adherence_percent,
                    p.overall_shrinkage, p.talk_time, p.staff_time,
                ]
                for p in data.trends.points
            ],
        ),
        (
            "Agents",
            [
                "Emp ID", "Name", "Process", "Days recorded", "Days present", "Login hrs",
                "Talk hrs", "Idle hrs", "Break hrs", "Late logins", "Early logouts", "Adherent days",
            ],
            [
                [
                    a.emp_id, a.employee_name, a.process, a.days_recorded, a.days_present,
                    a.login_hours, a.talk_time, a.idle_time, a.break_time, a.late_logins,
                    a.early_logouts, a.adherent_days,
                ]
                for a in data.agents
            ],
        ),
    ]


def _project_tables(data: ReportData) -> list[tuple[str, list[str], list[list]]]:
    if data.projects is None:
        return []
    report = data.projects
    return [
        (
            "Projects",
            ["Project", "Client", "Total hrs", "Billable hrs", "Employees", "Share %"],
            [
                [p.project_name, p.client_name, p.total_hours, p.billable_hours, p.employees, p.share_percent]
                for p in report.projects
            ],
        ),
        (
            "Project employees",
            ["Emp ID", "Name", "Total hrs", "Billable hrs", "Billable %", "Projects", "Days logged"],
            [
                [
                    e.emp_id, e.employee_name, e.total_hours, e.billable_hours,
                    e.billable_percent, e.projects, e.days_logged,
                ]
                for e in report.employees
            ],
        ),
        (
            "Bench",
            ["Emp ID", "Name", "Process", "Designation", "Manager", "TL"],
            [
                [b.emp_id, b.employee_name, b.process, b.designation, b.manager_name, b.tl_name]
                for b in report.bench
            ],
        ),
        (
            "Project daily trend",
            ["Date", "Total hrs", "Billable hrs"],
            [[p.report_date, p.total_hours, p.billable_hours] for p in report.trends],
        ),
    ]


def _hiring_tables(data: ReportData) -> list[tuple[str, list[str], list[list]]]:
    if data.hiring is None:
        return []
    report = data.hiring
    return [
        (
            "Hiring monthly",
            ["Month", "Joiners", "Leavers"],
            [[p.month, p.joiners, p.leavers] for p in report.trends],
        ),
        (
            "Hiring teams",
            ["Team", "Joiners", "Leavers", "Net change"],
            [[t.team, t.joiners, t.leavers, t.net_change] for t in report.teams],
        ),
        (
            "Joiners and leavers",
            ["Emp ID", "Name", "Event", "Date", "Team", "Designation", "Manager", "Detail"],
            [
                [
                    e.emp_id, e.employee_name, e.event_type, e.event_date, e.team,
                    e.designation, e.manager_name, e.detail,
                ]
                for e in report.events
            ],
        ),
    ]


def _uploads_tables(data: ReportData) -> list[tuple[str, list[str], list[list]]]:
    if data.uploads is None:
        return []
    report = data.uploads
    return [
        (
            "Uploads by type",
            ["Report type", "Uploads", "Completed", "Failed", "Rows imported", "Rows skipped"],
            [
                [t.report_type, t.uploads, t.completed, t.failed, t.rows_processed, t.rows_skipped]
                for t in report.by_type
            ],
        ),
        (
            "Upload issues",
            ["Uploaded", "File", "Report type", "Status", "Uploaded by", "Rows skipped", "Details"],
            [
                [
                    i.uploaded_at.strftime("%Y-%m-%d %H:%M"), i.file_name, i.report_type,
                    i.status, i.uploaded_by, i.rows_skipped, i.message,
                ]
                for i in report.issues
            ],
        ),
        (
            "Days with no upload",
            ["Date"],
            [[day] for day in report.days_without_upload],
        ),
    ]


def _utilization_tables(data: ReportData) -> list[tuple[str, list[str], list[list]]]:
    if data.utilization is None:
        return []
    return [
        (
            "Utilization",
            [
                "Emp ID", "Name", "Total hrs", "Billable hrs", "Capacity hrs",
                "Utilization %", "Billable util %", "Status",
            ],
            [
                [
                    r.emp_id, r.employee_name, r.total_hours, r.billable_hours, r.capacity_hours,
                    r.utilization_percent, r.billable_utilization_percent, r.status,
                ]
                for r in data.utilization.rows
            ],
        ),
    ]


def report_tables(data: ReportData) -> list[tuple[str, list[str], list[list]]]:
    return (
        _agent_tables(data)
        + _project_tables(data)
        + _hiring_tables(data)
        + _utilization_tables(data)
        + _uploads_tables(data)
    )


# --- Excel ---------------------------------------------------------------------

_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_FILL = PatternFill("solid", fgColor="1F4E78")


def _write_header(sheet, row: int, headers: list[str]) -> None:
    for column, header in enumerate(headers, start=1):
        cell = sheet.cell(row=row, column=column, value=header)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal="center")


def _autosize(sheet) -> None:
    for column_cells in sheet.columns:
        longest = max((len(str(cell.value)) for cell in column_cells if cell.value is not None), default=8)
        sheet.column_dimensions[get_column_letter(column_cells[0].column)].width = min(longest + 2, 45)


def _add_table_sheet(workbook: Workbook, title: str, headers: list[str], rows: list[list]) -> None:
    sheet = workbook.create_sheet(title)
    _write_header(sheet, 1, headers)
    for row_number, row in enumerate(rows, start=2):
        sheet.append(row)
        for cell in sheet[row_number]:
            if isinstance(cell.value, date):
                cell.number_format = "yyyy-mm-dd"
    sheet.freeze_panes = "A2"
    _autosize(sheet)


def build_xlsx(data: ReportData) -> bytes:
    workbook = Workbook()

    summary = workbook.active
    summary.title = "Summary"
    summary["A1"] = data.title
    summary["A1"].font = Font(bold=True, size=14)
    summary["A2"] = f"Period: {data.period_text}"
    summary["A3"] = f"Generated: {data.generated_at:%Y-%m-%d %H:%M}"

    row = 4
    for note in missing_notes(data):
        summary.cell(row=row, column=1, value=note).font = Font(bold=True, color="C00000")
        row += 1
    row += 1

    for heading, rows in summary_blocks(data):
        summary.cell(row=row, column=1, value=heading).font = Font(bold=True, size=12)
        row += 1
        _write_header(summary, row, ["Metric", "Value"])
        for label, value in rows:
            row += 1
            summary.cell(row=row, column=1, value=label)
            summary.cell(row=row, column=2, value=value)
        row += 2
    _autosize(summary)

    for title, headers, rows in report_tables(data):
        _add_table_sheet(workbook, title, headers, rows)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


# --- PDF -----------------------------------------------------------------------


def _pdf_cell(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)[:30]


def build_pdf(data: ReportData) -> bytes:
    # Imported here so the rest of the app still starts if reportlab is missing.
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=data.title,
    )

    def table(rows: list[list], widths: list[float] | None = None) -> Table:
        built = Table(rows, colWidths=widths, repeatRows=1)
        built.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
                ]
            )
        )
        return built

    story = [
        Paragraph(data.title, styles["Title"]),
        Paragraph(f"Period: {data.period_text} &nbsp;&nbsp; Generated: {data.generated_at:%Y-%m-%d %H:%M}", styles["Normal"]),
        Spacer(1, 4 * mm),
    ]
    for note in missing_notes(data):
        story += [Paragraph(f"<font color='#C00000'>{note}</font>", styles["Normal"]), Spacer(1, 2 * mm)]

    for heading, rows in summary_blocks(data):
        story += [Spacer(1, 4 * mm), Paragraph(heading, styles["Heading2"])]
        story.append(table([["Metric", "Value"], *[[label, value] for label, value in rows]], [90 * mm, 40 * mm]))

    for title, headers, rows in report_tables(data):
        if not rows:
            continue
        story += [Spacer(1, 6 * mm), Paragraph(title, styles["Heading2"])]
        shown = rows[:PDF_MAX_ROWS]
        story.append(table([headers, *[[_pdf_cell(value) for value in row] for row in shown]]))
        if len(rows) > PDF_MAX_ROWS:
            story.append(
                Paragraph(
                    f"Showing {PDF_MAX_ROWS} of {len(rows)} rows. The Excel report lists all of them.",
                    styles["Italic"],
                )
            )

    document.build(story)
    return buffer.getvalue()


CONTENT_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


def render_report(data: ReportData, file_format: str) -> bytes:
    if file_format == "xlsx":
        return build_xlsx(data)
    if file_format == "pdf":
        return build_pdf(data)
    raise ValueError(f"Unknown report format: {file_format}")


# --- Saving and emailing ---------------------------------------------------------


def save_report_files(data: ReportData, directory: Path | None = None) -> list[Path]:
    """Write the Excel and PDF versions to storage/reports and return their paths."""
    target = directory or settings.REPORTS_PATH
    target.mkdir(parents=True, exist_ok=True)
    paths = []
    for file_format in ("xlsx", "pdf"):
        path = target / f"{data.file_stem}.{file_format}"
        path.write_bytes(render_report(data, file_format))
        paths.append(path)
    return paths


def email_enabled() -> bool:
    return bool(settings.SMTP_HOST and settings.REPORT_EMAIL_LIST)


def email_report_files(data: ReportData, paths: list[Path]) -> None:
    message = EmailMessage()
    message["Subject"] = f"{data.title}: {data.period_text}"
    message["From"] = settings.SMTP_FROM or settings.SMTP_USER
    message["To"] = ", ".join(settings.REPORT_EMAIL_LIST)
    message.set_content(f"The {data.kind} MIS report for {data.period_text} is attached.")
    for path in paths:
        subtype = "pdf" if path.suffix == ".pdf" else "vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        message.add_attachment(path.read_bytes(), maintype="application", subtype=subtype, filename=path.name)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
        server.starttls()
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(message)


def generate_scheduled_report(db: Session, kind: str, today: date) -> list[Path]:
    """Build one scheduled report for the unrestricted view, save it, and email it."""
    date_from, date_to = period_for(kind, today)
    data = build_report_data(db, kind, date_from, date_to, scope=None)
    paths = save_report_files(data)
    logger.info("Saved %s report for %s: %s", kind, data.period_text, [p.name for p in paths])
    if email_enabled():
        try:
            email_report_files(data, paths)
        except Exception:
            # The files are saved either way; a mail problem must not lose the report.
            logger.exception("Could not email the %s report", kind)
    return paths
