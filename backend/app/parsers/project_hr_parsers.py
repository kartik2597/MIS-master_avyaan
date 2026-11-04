"""Importers for the project timesheet and the hiring / attrition reports.

  PROJECT_TIMESHEET  -> project_timesheets  (hours per employee, project and day)
  HIRING_ATTRITION   -> employee_movements  (one row per joiner or leaver)

They use the same building blocks as the workbook parsers: header aliases are
resolved through the report registry, a bad row is skipped with a reason (the
rest of the file still imports), and a re-upload updates rows instead of
duplicating them.
"""

import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.employee_movement import EVENT_JOINED, EVENT_LEFT, EmployeeMovement
from app.models.project_timesheet import ProjectTimesheet
from app.models.raw_report_record import RawReportRecord
from app.parsers.row_checks import check_report_row, load_known_emp_ids
from app.parsers.upload_status import RowError
from app.parsers.utils import is_blank, parse_bool, parse_date
from app.parsers.workbook_parsers import (
    NOT_PROVIDED,
    ROW_ERRORS,
    SECONDS_PER_HOUR,
    TWO_PLACES,
    canonical_row,
    hours_to_seconds,
    required_text,
    run_import,
    text_value,
)
from app.reports.headers import normalize_column_name
from app.reports.report_types import ReportType
from app.services.employee_sync import sync_employees_from_report_rows


logger = logging.getLogger(__name__)

# One timesheet entry is a single person's hours for one project on one day.
MAX_HOURS_PER_ENTRY = Decimal("24")

BILLABLE_WORDS = {"yes", "y", "true", "1", "billable"}
NON_BILLABLE_WORDS = {
    "no",
    "n",
    "false",
    "0",
    "non billable",
    "nonbillable",
    "not billable",
    "bench",
}

# What the "Event Type" column may say, after spaces/underscores are normalized.
JOINED_WORDS = {"joined", "joiner", "new joiner", "hired", "hire", "new hire", "joining", "onboarded"}
LEFT_WORDS = {
    "left",
    "exit",
    "exited",
    "resigned",
    "resignation",
    "terminated",
    "termination",
    "absconded",
    "separated",
    "released",
    "attrition",
}
# Words that only say "this person left", so they are no use as a reason.
GENERIC_LEFT_WORDS = {"left", "exit", "exited", "separated", "attrition"}


# --- Project timesheet -> project_timesheets ---------------------------------


def map_timesheet_row(raw_data: dict[str, Any]) -> dict[str, Any]:
    row = canonical_row(raw_data, ReportType.PROJECT_TIMESHEET)

    hours_value = row.get("Hours Logged")
    if is_blank(hours_value):
        raise ValueError("Missing required column value: Hours Logged")
    hours = (hours_to_seconds(hours_value) / SECONDS_PER_HOUR).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )
    if hours <= 0:
        raise ValueError(f"Hours logged must be above 0 (got {hours})")
    if hours > MAX_HOURS_PER_ENTRY:
        raise ValueError(f"Hours logged is above {MAX_HOURS_PER_ENTRY} for one day ({hours})")

    return {
        "emp_id": required_text(row, "Employee ID"),
        "employee_name": required_text(row, "Employee Name"),
        "report_date": parse_date(row.get("Work Date")),
        "project_name": required_text(row, "Project Name"),
        "client_name": text_value(row, "Client Name", NOT_PROVIDED),
        "task_type": text_value(row, "Task Type", "General"),
        # Hours on a project count as billable unless the file says otherwise.
        "billable": parse_bool(
            row.get("Billable"),
            default=True,
            true_values=BILLABLE_WORDS,
            false_values=NON_BILLABLE_WORDS,
        ),
        "hours": hours,
    }


def upsert_project_timesheets(db: Session, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    existing = {
        (record.emp_id, record.report_date, record.project_name, record.task_type): record
        for record in db.scalars(
            select(ProjectTimesheet).where(
                ProjectTimesheet.emp_id.in_({row["emp_id"] for row in rows}),
                ProjectTimesheet.report_date.in_({row["report_date"] for row in rows}),
            )
        ).all()
    }
    for row in rows:
        key = (row["emp_id"], row["report_date"], row["project_name"], row["task_type"])
        record = existing.get(key)
        if record is None:
            db.add(ProjectTimesheet(**row))
            continue
        for field_name, value in row.items():
            setattr(record, field_name, value)
    db.commit()


def process_project_timesheets(
    db: Session, upload_id: UUID, raw_records: list[RawReportRecord]
) -> list[RowError]:
    known_emp_ids = load_known_emp_ids(db)
    rows: list[dict[str, Any]] = []
    errors: list[RowError] = []

    for record in raw_records:
        try:
            row = map_timesheet_row(record.raw_data)
            check_report_row(row, known_emp_ids=known_emp_ids)
        except ROW_ERRORS as exc:
            logger.warning("Timesheet row %s skipped: %s", record.row_number, exc)
            errors.append((record.row_number, str(exc)))
            continue
        row["upload_id"] = upload_id
        rows.append(row)

    latest_by_key = {
        (row["emp_id"], row["report_date"], row["project_name"], row["task_type"]): row
        for row in rows
    }
    upsert_project_timesheets(db, list(latest_by_key.values()))
    # Anyone who logged hours but is not in Employee Master yet is added to it, so
    # they can be found by team and appear on the right manager's dashboard.
    created = sync_employees_from_report_rows(
        db, list(latest_by_key.values()), upload_id
    )
    if created:
        logger.info("Timesheet upload %s added %s new employee(s)", upload_id, created)

    duplicates = len(rows) - len(latest_by_key)
    if duplicates:
        errors.append(
            (
                0,
                f"{duplicates} duplicate row(s) for the same employee, day, project and "
                "task; the last one was kept",
            )
        )
    return errors


def parse_project_timesheet_upload(db: Session, upload_id: UUID) -> dict[str, int]:
    return run_import(
        db,
        upload_id,
        ReportType.PROJECT_TIMESHEET,
        "PROJECT_TIMESHEET",
        process_project_timesheets,
    )


# --- Hiring / attrition -> employee_movements --------------------------------


def classify_event(value: str) -> str:
    """"Resigned" / "Terminated" / "Left" -> LEFT; "Joined" / "New Hire" -> JOINED."""
    words = normalize_column_name(value)
    if words in JOINED_WORDS:
        return EVENT_JOINED
    if words in LEFT_WORDS:
        return EVENT_LEFT
    raise ValueError(
        f"Unknown event type '{value}'. Use Joined, or Left / Resigned / Terminated"
    )


def map_movement_row(raw_data: dict[str, Any]) -> dict[str, Any]:
    row = canonical_row(raw_data, ReportType.HIRING_ATTRITION)
    event_text = required_text(row, "Event Type")
    event_type = classify_event(event_text)

    reason = text_value(row, "Exit Reason", "") or ""
    if event_type == EVENT_LEFT and not reason:
        # "Resigned" or "Terminated" in the event column is already a useful reason.
        if normalize_column_name(event_text) not in GENERIC_LEFT_WORDS:
            reason = event_text.strip().title()

    return {
        "emp_id": required_text(row, "Employee ID"),
        "employee_name": required_text(row, "Employee Name"),
        "event_type": event_type,
        "report_date": parse_date(row.get("Event Date")),
        "team": text_value(row, "Team", NOT_PROVIDED),
        "designation": text_value(row, "Designation", NOT_PROVIDED),
        "manager_name": text_value(row, "Manager Name", NOT_PROVIDED),
        "reason": reason if event_type == EVENT_LEFT else "",
        "hiring_source": (text_value(row, "Hiring Source", "") or "")
        if event_type == EVENT_JOINED
        else "",
    }


def fill_movements_from_master(db: Session, rows: list[dict[str, Any]]) -> None:
    """Use the employee master's process / designation / manager where the file left them out."""
    emp_ids = {row["emp_id"] for row in rows}
    if not emp_ids:
        return
    employees = {
        employee.emp_id: employee
        for employee in db.scalars(
            select(Employee).where(Employee.emp_id.in_(emp_ids))
        ).all()
    }
    for row in rows:
        employee = employees.get(row["emp_id"])
        if employee is None:
            continue
        if row["team"] == NOT_PROVIDED and employee.process:
            row["team"] = employee.process
        if row["designation"] == NOT_PROVIDED and employee.designation:
            row["designation"] = employee.designation
        if row["manager_name"] == NOT_PROVIDED and employee.manager_name:
            row["manager_name"] = employee.manager_name


def upsert_employee_movements(db: Session, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    existing = {
        (record.emp_id, record.event_type, record.report_date): record
        for record in db.scalars(
            select(EmployeeMovement).where(
                EmployeeMovement.emp_id.in_({row["emp_id"] for row in rows}),
                EmployeeMovement.report_date.in_({row["report_date"] for row in rows}),
            )
        ).all()
    }
    for row in rows:
        key = (row["emp_id"], row["event_type"], row["report_date"])
        record = existing.get(key)
        if record is None:
            db.add(EmployeeMovement(**row))
            continue
        for field_name, value in row.items():
            setattr(record, field_name, value)
    db.commit()


def movement_sync_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Hiring / exit rows in the shape the employee sync understands.

    A joiner's joining date is the event date. A leaver who is not in the master
    is added as Resigned, so they never show up as active or on the bench. Rows
    go in date order, so when someone both joined and left, the later event wins.
    """
    return [
        {
            "emp_id": row["emp_id"],
            "employee_name": row["employee_name"],
            "process": row["team"],
            "designation": row["designation"],
            "manager_name": row["manager_name"],
            "report_date": row["report_date"],
            "date_of_joining": row["report_date"] if row["event_type"] == EVENT_JOINED else None,
            "status": "Active" if row["event_type"] == EVENT_JOINED else "Resigned",
            "upload_id": row["upload_id"],
        }
        for row in sorted(rows, key=lambda item: item["report_date"])
    ]


def process_employee_movements(
    db: Session, upload_id: UUID, raw_records: list[RawReportRecord]
) -> list[RowError]:
    known_emp_ids = load_known_emp_ids(db)
    rows: list[dict[str, Any]] = []
    errors: list[RowError] = []

    for record in raw_records:
        try:
            row = map_movement_row(record.raw_data)
            # A joiner is usually not in the employee master yet, so only a leaver
            # has to be someone we already know.
            check_report_row(
                row,
                known_emp_ids=known_emp_ids if row["event_type"] == EVENT_LEFT else None,
            )
        except ROW_ERRORS as exc:
            logger.warning("Hiring/attrition row %s skipped: %s", record.row_number, exc)
            errors.append((record.row_number, str(exc)))
            continue
        row["upload_id"] = upload_id
        rows.append(row)

    latest_by_key = {
        (row["emp_id"], row["event_type"], row["report_date"]): row for row in rows
    }
    final_rows = list(latest_by_key.values())
    fill_movements_from_master(db, final_rows)
    upsert_employee_movements(db, final_rows)
    # Joiners (and leavers) missing from Employee Master are added to it.
    created = sync_employees_from_report_rows(db, movement_sync_rows(final_rows), upload_id)
    if created:
        logger.info("Hiring upload %s added %s new employee(s)", upload_id, created)

    duplicates = len(rows) - len(latest_by_key)
    if duplicates:
        errors.append(
            (0, f"{duplicates} duplicate row(s) for the same employee, event and date; the last one was kept")
        )
    return errors


def parse_employee_movement_upload(db: Session, upload_id: UUID) -> dict[str, int]:
    return run_import(
        db,
        upload_id,
        ReportType.HIRING_ATTRITION,
        "HIRING_ATTRITION",
        process_employee_movements,
    )


__all__ = [
    "classify_event",
    "map_movement_row",
    "map_timesheet_row",
    "parse_employee_movement_upload",
    "parse_project_timesheet_upload",
]
