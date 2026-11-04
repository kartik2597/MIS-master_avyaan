"""Daily, weekly and monthly MIS reports as Excel and PDF files.

The numbers come from the same functions the dashboard uses (get_dashboard_kpis,
get_dashboard_trends, get_dashboard_agents), so an exported report always agrees
with what the dashboard shows for the same dates and team.
"""

import logging
import smtplib
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path
from typing import Literal

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import Select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.dashboard import DashboardAgentRow, DashboardKpis, DashboardTrends
from app.services.dashboard import (
    get_dashboard_agents,
    get_dashboard_kpis,
    get_dashboard_trends,
)


logger = logging.getLogger(__name__)

ReportKind = Literal["daily", "weekly", "monthly"]
ReportFormat = Literal["xlsx", "pdf"]

REPORT_KINDS: tuple[str, ...] = ("daily", "weekly", "monthly")
# The PDF lists at most this many agents; the Excel file always has all of them.
PDF_MAX_AGENTS = 200


@dataclass
class ReportData:
    kind: str
    date_from: date
    date_to: date
    generated_at: datetime
    kpis: DashboardKpis
    trends: DashboardTrends
    agents: list[DashboardAgentRow]

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


def build_report_data(
    db: Session,
    kind: str,
    date_from: date,
    date_to: date,
    scope: Select | None = None,
) -> ReportData:
    return ReportData(
        kind=kind,
        date_from=date_from,
        date_to=date_to,
        generated_at=datetime.now(),
        kpis=get_dashboard_kpis(db, date_from=date_from, date_to=date_to, scope=scope),
        trends=get_dashboard_trends(db, date_from=date_from, date_to=date_to, scope=scope),
        agents=get_dashboard_agents(
            db,
            date_from=date_from,
            date_to=date_to,
            page=1,
            page_size=1_000_000,
            scope=scope,
        ).items,
    )


def _percent_of(part: float, whole: float) -> str:
    return f"{part * 100 / whole:.2f}%" if whole > 0 else "-"


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


def _missing_note(kpis: DashboardKpis) -> str | None:
    if not kpis.missing_reports:
        return None
    return "No data uploaded for: " + ", ".join(kpis.missing_reports) + ". Related figures show 0."


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


def build_xlsx(data: ReportData) -> bytes:
    workbook = Workbook()

    summary = workbook.active
    summary.title = "Summary"
    summary["A1"] = data.title
    summary["A1"].font = Font(bold=True, size=14)
    summary["A2"] = f"Period: {data.period_text}"
    summary["A3"] = f"Generated: {data.generated_at:%Y-%m-%d %H:%M}"
    note = _missing_note(data.kpis)
    first_row = 5
    if note:
        summary["A4"] = note
        summary["A4"].font = Font(bold=True, color="C00000")
    _write_header(summary, first_row, ["Metric", "Value"])
    for offset, (label, value) in enumerate(kpi_rows(data.kpis), start=1):
        summary.cell(row=first_row + offset, column=1, value=label)
        summary.cell(row=first_row + offset, column=2, value=value)
    _autosize(summary)

    trend = workbook.create_sheet("Daily trend")
    _write_header(
        trend,
        1,
        ["Date", "Head count", "Present", "Adherence %", "Shrinkage %", "Talk hrs", "Staff hrs"],
    )
    for row, point in enumerate(data.trends.points, start=2):
        trend.append(
            [
                point.report_date,
                point.head_count,
                point.present_count,
                point.adherence_percent,
                point.overall_shrinkage,
                point.talk_time,
                point.staff_time,
            ]
        )
        trend.cell(row=row, column=1).number_format = "yyyy-mm-dd"
    _autosize(trend)

    agents = workbook.create_sheet("Agents")
    _write_header(
        agents,
        1,
        [
            "Emp ID", "Name", "Process", "Days recorded", "Days present", "Login hrs",
            "Talk hrs", "Idle hrs", "Break hrs", "Late logins", "Early logouts", "Adherent days",
        ],
    )
    for agent in data.agents:
        agents.append(
            [
                agent.emp_id, agent.employee_name, agent.process, agent.days_recorded,
                agent.days_present, agent.login_hours, agent.talk_time, agent.idle_time,
                agent.break_time, agent.late_logins, agent.early_logouts, agent.adherent_days,
            ]
        )
    agents.freeze_panes = "A2"
    _autosize(agents)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


# --- PDF -----------------------------------------------------------------------


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
    note = _missing_note(data.kpis)
    if note:
        story += [Paragraph(f"<font color='#C00000'>{note}</font>", styles["Normal"]), Spacer(1, 3 * mm)]

    story.append(table([["Metric", "Value"], *[[label, value] for label, value in kpi_rows(data.kpis)]], [90 * mm, 40 * mm]))

    if data.trends.points:
        story += [Spacer(1, 6 * mm), Paragraph("Daily trend", styles["Heading2"])]
        rows = [["Date", "Head count", "Present", "Adherence %", "Shrinkage %", "Talk hrs", "Staff hrs"]]
        for point in data.trends.points:
            rows.append(
                [
                    point.report_date.isoformat(),
                    point.head_count,
                    point.present_count,
                    "-" if point.adherence_percent is None else f"{point.adherence_percent:.2f}",
                    "-" if point.overall_shrinkage is None else f"{point.overall_shrinkage:.2f}",
                    f"{point.talk_time:.2f}",
                    f"{point.staff_time:.2f}",
                ]
            )
        story.append(table(rows))

    if data.agents:
        story += [Spacer(1, 6 * mm), Paragraph("Agents", styles["Heading2"])]
        rows = [["Emp ID", "Name", "Process", "Days", "Present", "Login hrs", "Talk hrs", "Late", "Early", "Adherent"]]
        for agent in data.agents[:PDF_MAX_AGENTS]:
            rows.append(
                [
                    agent.emp_id, agent.employee_name[:28], agent.process[:22], agent.days_recorded,
                    agent.days_present, f"{agent.login_hours:.2f}", f"{agent.talk_time:.2f}",
                    agent.late_logins, agent.early_logouts, agent.adherent_days,
                ]
            )
        story.append(table(rows))
        if len(data.agents) > PDF_MAX_AGENTS:
            story.append(
                Paragraph(
                    f"Showing {PDF_MAX_AGENTS} of {len(data.agents)} agents. The Excel report lists all of them.",
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
