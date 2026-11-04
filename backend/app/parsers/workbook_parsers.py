"""Importers for the compact "test data" workbook format: one sheet per report.

  EMPLOYEE_ROSTER  -> employees
  DAILY_ACTIVITY   -> agent_daily_performance (+ agent_shift_adherence for present agents)
  SHRINKAGE_HOURS  -> agent_shrinkage

Values arrive in HOURS ("Login_Hours" 8.78); the tables store SECONDS, because the
dashboard converts seconds back to hours. Column names are resolved through the
report's header aliases, so "Emp Code", "Employee_ID" and "employee id" all work.

Business rules the source data does not define (see the workbook's Metric_Guide)
are the two constants below. Change them to match company policy.
"""

import logging
from collections.abc import Callable
from datetime import date, time
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_daily_performance import AgentDailyPerformance
from app.models.agent_shift_adherence import AgentShiftAdherence
from app.models.agent_shrinkage import AgentShrinkage
from app.models.employee import Employee
from app.models.raw_report_record import RawReportRecord
from app.models.upload_history import UploadHistory
from app.parsers.apr_parser import upsert_agent_daily_performance
from app.parsers.shift_adherence_parser import upsert_agent_shift_adherence
from app.parsers.shrinkage_parser import upsert_agent_shrinkage
from app.parsers.upload_status import (
    RowError,
    mark_upload_completed,
    mark_upload_failed,
    mark_upload_processing,
)
from app.parsers.utils import (
    clean_value,
    is_blank,
    parse_date,
    parse_decimal,
    parse_time,
    time_to_seconds,
)
from app.reports.headers import map_uploaded_columns
from app.reports.registry import get_header_lookup
from app.reports.report_types import ReportType


logger = logging.getLogger(__name__)

# A login this many minutes after shift start (or logout this many minutes before
# shift end) is still on time.
SHIFT_GRACE_MINUTES = 0
# Denominator for shrinkage %: scheduled hours in one agent-day.
SCHEDULED_HOURS_PER_SHIFT = Decimal("9")

NOT_PROVIDED = "N/A"
SECONDS_PER_HOUR = Decimal("3600")
TWO_PLACES = Decimal("0.01")
ADHERENT_WORDS = {"adherent", "adhere", "adhered", "adherence", "yes", "y", "true", "1"}


# --- Shared helpers ----------------------------------------------------------


def canonical_row(raw_data: dict[str, Any], report_type: ReportType) -> dict[str, Any]:
    """Raw file row -> {canonical column name: cleaned value}, aliases resolved."""
    mapping = map_uploaded_columns(raw_data.keys(), get_header_lookup(report_type))
    return {
        canonical: clean_value(raw_data[uploaded])
        for uploaded, canonical in mapping.items()
    }


def text_value(row: dict[str, Any], name: str, default: str | None = None) -> str | None:
    value = row.get(name)
    if is_blank(value):
        return default
    if isinstance(value, float) and value.is_integer():
        value = int(value)  # employee id 1001.0 -> "1001"
    return str(value).strip()


def required_text(row: dict[str, Any], name: str) -> str:
    value = text_value(row, name)
    if value is None:
        raise ValueError(f"Missing required column value: {name}")
    return value


def hours_to_seconds(value: Any) -> Decimal:
    """8.78 -> 31608.00 seconds. Also accepts "08:30" / "08:30:00". Blank -> 0."""
    value = clean_value(value)
    if is_blank(value):
        return Decimal("0")
    if isinstance(value, str) and ":" in value:
        clock_text = value if value.count(":") == 2 else f"{value}:00"
        return Decimal(time_to_seconds(clock_text))
    seconds = (parse_decimal(value) * SECONDS_PER_HOUR).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )
    if seconds < 0:
        raise ValueError(f"Hours cannot be negative: {value}")
    return seconds


def first_present(row: dict[str, Any], *names: str) -> Any:
    for name in names:
        if not is_blank(row.get(name)):
            return row[name]
    return None


def blank_record(raw_data: dict[str, Any]) -> bool:
    return all(is_blank(value) for value in raw_data.values())


def attendance_counts(attendance: str) -> dict[str, int]:
    kind = attendance.strip().lower()
    counts = {
        "present_count": 0,
        "absent_count": 0,
        "lwp_count": 0,
        "cl_count": 0,
        "half_day_count": 0,
        "training_count": 0,
    }
    if kind in {"present", "p"}:
        counts["present_count"] = 1
    elif kind in {"absent", "a"}:
        counts["absent_count"] = 1
    elif kind in {"leave", "cl"}:
        counts["cl_count"] = 1
    elif kind == "lwp":
        counts["lwp_count"] = 1
    elif kind in {"half day", "half-day", "hd"}:
        counts["half_day_count"] = 1
    return counts


def tenure_bucket(age_days: int) -> str:
    if age_days <= 30:
        return "0-30 days"
    if age_days <= 90:
        return "31-90 days"
    if age_days <= 180:
        return "91-180 days"
    if age_days <= 365:
        return "181-365 days"
    return "365+ days"


# --- Shared import runner ----------------------------------------------------


def run_import(
    db: Session,
    upload_id: UUID,
    report_type: ReportType,
    label: str,
    process_records: Callable[[Session, UUID, list[RawReportRecord]], list[RowError]],
) -> dict[str, int]:
    upload_history = db.get(UploadHistory, upload_id)
    if upload_history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload history not found",
        )
    if upload_history.report_type != report_type.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload is not a {label} report",
        )

    mark_upload_processing(db=db, upload_history=upload_history)
    total_records = processed_records = failed_records = 0

    try:
        raw_records = list(
            db.scalars(
                select(RawReportRecord)
                .where(
                    RawReportRecord.upload_id == upload_id,
                    RawReportRecord.report_type == report_type.value,
                )
                .order_by(RawReportRecord.row_number.asc())
            ).all()
        )
        raw_records = [record for record in raw_records if not blank_record(record.raw_data)]
        total_records = len(raw_records)

        row_errors = process_records(db, upload_id, raw_records)
        failed_records = len(row_errors)
        processed_records = max(total_records - failed_records, 0)

        mark_upload_completed(
            db=db,
            upload_history=upload_history,
            total_records=total_records,
            processed_records=processed_records,
            failed_records=failed_records,
            row_errors=row_errors,
        )
        return {
            "total_records": total_records,
            "processed_records": processed_records,
            "failed_records": failed_records,
        }
    except Exception as exc:
        db.rollback()
        mark_upload_failed(
            db=db,
            upload_history=upload_history,
            total_records=total_records,
            processed_records=processed_records,
            failed_records=failed_records,
            error_message=str(exc),
        )
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{label} import failed",
        ) from exc


ROW_ERRORS = (TypeError, ValueError, ArithmeticError)


# --- Employee roster -> employees --------------------------------------------


def map_employee_roster_row(raw_data: dict[str, Any]) -> dict[str, Any]:
    row = canonical_row(raw_data, ReportType.EMPLOYEE_ROSTER)
    team = required_text(row, "Team")
    return {
        "emp_id": required_text(row, "Employee ID"),
        "employee_name": required_text(row, "Employee Name"),
        "department": team,
        "process": team,
        "designation": required_text(row, "Designation"),
        "date_of_joining": parse_date(row.get("Date Of Joining")),
        "employment_status": required_text(row, "Employment Status"),
    }


def process_employee_roster(
    db: Session, upload_id: UUID, raw_records: list[RawReportRecord]
) -> list[RowError]:
    rows: list[dict[str, Any]] = []
    errors: list[RowError] = []
    for record in raw_records:
        try:
            rows.append(map_employee_roster_row(record.raw_data))
        except ROW_ERRORS as exc:
            logger.warning("Roster row %s skipped: %s", record.row_number, exc)
            errors.append((record.row_number, str(exc)))

    latest_by_emp_id = {row["emp_id"]: row for row in rows}
    existing = {
        employee.emp_id: employee
        for employee in db.scalars(
            select(Employee).where(Employee.emp_id.in_(list(latest_by_emp_id)))
        ).all()
    } if latest_by_emp_id else {}

    for emp_id, data in latest_by_emp_id.items():
        employee = existing.get(emp_id)
        if employee is None:
            # The roster has no contact details; the table needs a value, so new
            # employees get blanks until a master database upload fills them in.
            db.add(
                Employee(
                    upload_id=upload_id,
                    email="",
                    mobile="",
                    manager_name="",
                    tl_name="",
                    location="",
                    **data,
                )
            )
        else:
            # Only the roster's own fields: never wipe email/mobile/manager that a
            # master database upload already filled in.
            for field_name, value in data.items():
                setattr(employee, field_name, value)
    db.commit()

    duplicates = len(rows) - len(latest_by_emp_id)
    if duplicates:
        errors.append(
            (0, f"{duplicates} duplicate Employee ID row(s); the last one was kept")
        )
    return errors


def parse_employee_roster_upload(db: Session, upload_id: UUID) -> dict[str, int]:
    return run_import(
        db, upload_id, ReportType.EMPLOYEE_ROSTER, "EMPLOYEE_ROSTER", process_employee_roster
    )


# --- Daily activity -> performance + shift adherence -------------------------


def minutes_of_day(value: time) -> int:
    return value.hour * 60 + value.minute


def late_and_early_minutes(
    shift_start: time, shift_end: time, login: time, logout: time
) -> tuple[int, int]:
    """Minutes late at login / early at logout, after the grace period.

    Handles shifts that end after midnight (22:00 -> 06:00).
    """
    start = minutes_of_day(shift_start)
    end = minutes_of_day(shift_end)
    if end <= start:
        end += 24 * 60
    login_minutes = minutes_of_day(login)
    if login_minutes < start - 12 * 60:
        login_minutes += 24 * 60
    logout_minutes = minutes_of_day(logout)
    if logout_minutes < login_minutes:
        logout_minutes += 24 * 60
    late = max(0, login_minutes - start - SHIFT_GRACE_MINUTES)
    early = max(0, end - logout_minutes - SHIFT_GRACE_MINUTES)
    return late, early


def build_shift_adherence_row(
    row: dict[str, Any],
    *,
    base: dict[str, Any],
    login_seconds: Decimal,
) -> dict[str, Any] | None:
    """Adherence applies to agents who were present and have shift + login times."""
    if base["attendance"].strip().lower() != "present":
        return None
    try:
        shift_start = parse_time(row.get("Shift Start"))
        shift_end = parse_time(row.get("Shift End"))
        login = parse_time(first_present(row, "Login Time", "First Login Time"))
        logout = parse_time(first_present(row, "Logout Time", "Last Logout Time"))
    except ValueError as exc:
        logger.info("No shift adherence row for %s: %s", base["emp_id"], exc)
        return None

    late, early = late_and_early_minutes(shift_start, shift_end, login, logout)
    reported = text_value(row, "Shift Adherence")
    if reported is None:
        reported = "Adherent" if late == 0 and early == 0 else "Non Adherent"
    adherent = reported.strip().lower() in ADHERENT_WORDS
    downtime = hours_to_seconds(row.get("Downtime Hours"))

    return {
        "emp_id": base["emp_id"],
        "employee_name": base["employee_name"],
        "report_date": base["report_date"],
        "status": "Active",
        "process": base["campaign"],
        "designation": NOT_PROVIDED,
        "manager_name": NOT_PROVIDED,
        "attendance": base["attendance"],
        "shift_start_time": shift_start,
        "shift_end_time": shift_end,
        "actual_login_time": login,
        "actual_logout_time": logout,
        "login_hours_seconds": int(login_seconds),
        "downtime_seconds": int(downtime),
        "login_plus_downtime_seconds": int(login_seconds + downtime),
        "shift_login_adherence_percent": Decimal("100") if adherent else Decimal("0"),
        "adherence_status": reported,
        "late_login_minutes": late,
        "early_logout_minutes": early,
        "adherence_flag": adherent,
        "non_adherence_flag": not adherent,
        "non_adherence_percent": Decimal("0") if adherent else Decimal("100"),
    }


def map_daily_activity_row(
    raw_data: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    row = canonical_row(raw_data, ReportType.DAILY_ACTIVITY)
    team = text_value(row, "Team", NOT_PROVIDED)
    login_seconds = hours_to_seconds(first_present(row, "Login Hours", "Total Login Hours"))
    staff_seconds = (
        hours_to_seconds(row["Staff Time Hours"])
        if not is_blank(row.get("Staff Time Hours"))
        else login_seconds
    )
    talk_seconds = hours_to_seconds(row.get("Talk Time Hours"))
    productivity = Decimal("0")
    if staff_seconds > 0:
        productivity = min(
            talk_seconds * 100 / staff_seconds, Decimal("100")
        ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    performance = {
        "emp_id": required_text(row, "Employee ID"),
        "employee_name": required_text(row, "Employee Name"),
        "report_date": parse_date(row.get("Work Date")),
        "campaign": team,
        "user_group": team,
        "attendance": required_text(row, "Attendance Status"),
        "login_hours": login_seconds,
        "staff_time": staff_seconds,
        "talk_time": talk_seconds,
        "break_time": hours_to_seconds(row.get("Break Time Hours")),
        "idle_time": hours_to_seconds(row.get("Idle Time Hours")),
        "productivity_percent": productivity,
        "total_calls": 0,
        "dialer_total_calls": 0,
        "dialflow_total_calls": 0,
        "connected_calls": 0,
        "not_connected_calls": 0,
        "positive_calls": 0,
        "conversion_percent": Decimal("0"),
        "tl_remark": "",
    }
    adherence = build_shift_adherence_row(
        row,
        base={**performance, "campaign": team},
        login_seconds=login_seconds,
    )
    return performance, adherence


def fill_from_roster(db: Session, adherence_rows: list[dict[str, Any]]) -> None:
    """Use the roster's designation / process when the employee is already known."""
    emp_ids = {row["emp_id"] for row in adherence_rows}
    if not emp_ids:
        return
    employees = {
        employee.emp_id: employee
        for employee in db.scalars(
            select(Employee).where(Employee.emp_id.in_(emp_ids))
        ).all()
    }
    for row in adherence_rows:
        employee = employees.get(row["emp_id"])
        if employee is None:
            continue
        row["designation"] = employee.designation or NOT_PROVIDED
        row["manager_name"] = employee.manager_name or NOT_PROVIDED
        row["status"] = employee.employment_status or row["status"]


def sync_shrinkage_attendance(db: Session, performance_rows: list[dict[str, Any]]) -> None:
    """Shrinkage rows carry attendance counts; refresh them when activity arrives later."""
    by_key = {(row["emp_id"], row["report_date"]): row for row in performance_rows}
    if not by_key:
        return
    records = db.scalars(
        select(AgentShrinkage).where(
            AgentShrinkage.emp_id.in_({key[0] for key in by_key}),
            AgentShrinkage.report_date.in_({key[1] for key in by_key}),
        )
    ).all()
    for record in records:
        source = by_key.get((record.emp_id, record.report_date))
        if source is None:
            continue
        record.attendance = source["attendance"]
        record.login_hours_seconds = int(source["login_hours"])
        for field_name, value in attendance_counts(source["attendance"]).items():
            setattr(record, field_name, value)
    db.commit()


def process_daily_activity(
    db: Session, upload_id: UUID, raw_records: list[RawReportRecord]
) -> list[RowError]:
    performance_rows: list[dict[str, Any]] = []
    adherence_rows: list[dict[str, Any]] = []
    errors: list[RowError] = []

    for record in raw_records:
        try:
            performance, adherence = map_daily_activity_row(record.raw_data)
        except ROW_ERRORS as exc:
            logger.warning("Daily activity row %s skipped: %s", record.row_number, exc)
            errors.append((record.row_number, str(exc)))
            continue
        performance["upload_id"] = upload_id
        performance_rows.append(performance)
        if adherence is not None:
            adherence["upload_id"] = upload_id
            adherence_rows.append(adherence)

    fill_from_roster(db, adherence_rows)
    upsert_agent_daily_performance(db=db, performance_rows=performance_rows)
    upsert_agent_shift_adherence(db=db, adherence_rows=adherence_rows)
    sync_shrinkage_attendance(db, performance_rows)
    return errors


def parse_daily_activity_upload(db: Session, upload_id: UUID) -> dict[str, int]:
    return run_import(
        db, upload_id, ReportType.DAILY_ACTIVITY, "DAILY_ACTIVITY", process_daily_activity
    )


# --- Shrinkage hours -> agent_shrinkage --------------------------------------


def map_shrinkage_hours_row(raw_data: dict[str, Any]) -> dict[str, Any]:
    row = canonical_row(raw_data, ReportType.SHRINKAGE_HOURS)
    return {
        "emp_id": required_text(row, "Employee ID"),
        "employee_name": required_text(row, "Employee Name"),
        "report_date": parse_date(row.get("Work Date")),
        "planned_hours": hours_to_seconds(row.get("Planned Shrinkage Hours")) / SECONDS_PER_HOUR,
        "unplanned_hours": hours_to_seconds(row.get("Unplanned Shrinkage Hours")) / SECONDS_PER_HOUR,
    }


def shrinkage_percent(hours: Decimal) -> Decimal:
    """Shrinkage hours as a % of one scheduled shift, capped at 100."""
    return min(hours * 100 / SCHEDULED_HOURS_PER_SHIFT, Decimal("100")).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )


def build_shrinkage_row(
    parsed: dict[str, Any],
    employee: Employee | None,
    activity: AgentDailyPerformance | None,
) -> dict[str, Any]:
    report_date: date = parsed["report_date"]
    joined = employee.date_of_joining if employee is not None else report_date
    age_days = max((report_date - joined).days, 0)
    attendance = activity.attendance if activity is not None else NOT_PROVIDED
    return {
        "emp_id": parsed["emp_id"],
        "employee_name": parsed["employee_name"],
        "report_date": report_date,
        "status": employee.employment_status if employee is not None else "Active",
        "process": employee.process if employee is not None else NOT_PROVIDED,
        "designation": employee.designation if employee is not None else NOT_PROVIDED,
        "manager_name": (employee.manager_name or NOT_PROVIDED)
        if employee is not None
        else NOT_PROVIDED,
        "date_of_joining": joined,
        "login_hours_seconds": int(activity.login_hours) if activity is not None else 0,
        "attendance": attendance,
        "employee_age_days": age_days,
        "tenure_bucket": tenure_bucket(age_days),
        "agent_count": 1,
        **attendance_counts(attendance),
        "planned_shrinkage": shrinkage_percent(parsed["planned_hours"]),
        "unplanned_shrinkage": shrinkage_percent(parsed["unplanned_hours"]),
        "opening_headcount": 0,
        "closing_headcount": 0,
        "attrition": 0,
    }


def process_shrinkage_hours(
    db: Session, upload_id: UUID, raw_records: list[RawReportRecord]
) -> list[RowError]:
    parsed_rows: list[dict[str, Any]] = []
    errors: list[RowError] = []
    for record in raw_records:
        try:
            parsed_rows.append(map_shrinkage_hours_row(record.raw_data))
        except ROW_ERRORS as exc:
            logger.warning("Shrinkage hours row %s skipped: %s", record.row_number, exc)
            errors.append((record.row_number, str(exc)))

    if parsed_rows:
        emp_ids = {row["emp_id"] for row in parsed_rows}
        dates = {row["report_date"] for row in parsed_rows}
        employees = {
            employee.emp_id: employee
            for employee in db.scalars(
                select(Employee).where(Employee.emp_id.in_(emp_ids))
            ).all()
        }
        activity: dict[tuple[str, date], AgentDailyPerformance] = {}
        for record in db.scalars(
            select(AgentDailyPerformance).where(
                AgentDailyPerformance.emp_id.in_(emp_ids),
                AgentDailyPerformance.report_date.in_(dates),
            )
        ).all():
            activity.setdefault((record.emp_id, record.report_date), record)

        shrinkage_rows = []
        for parsed in parsed_rows:
            row = build_shrinkage_row(
                parsed,
                employees.get(parsed["emp_id"]),
                activity.get((parsed["emp_id"], parsed["report_date"])),
            )
            row["upload_id"] = upload_id
            shrinkage_rows.append(row)
        upsert_agent_shrinkage(db=db, shrinkage_rows=shrinkage_rows)
    return errors


def parse_shrinkage_hours_upload(db: Session, upload_id: UUID) -> dict[str, int]:
    return run_import(
        db, upload_id, ReportType.SHRINKAGE_HOURS, "SHRINKAGE_HOURS", process_shrinkage_hours
    )
