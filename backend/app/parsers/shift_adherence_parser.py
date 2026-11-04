import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_shift_adherence import AgentShiftAdherence
from app.models.raw_report_record import RawReportRecord
from app.models.upload_history import UploadHistory
from app.parsers.row_checks import check_report_row, load_known_emp_ids
from app.parsers.upload_status import (
    RowError,
    mark_upload_completed,
    mark_upload_failed,
    mark_upload_processing,
)
from app.parsers.utils import (
    duration_to_minutes,
    get_raw_value,
    parse_bool,
    parse_date,
    parse_percent,
    parse_time,
    require_raw_value,
    time_to_seconds,
)
from app.reports.report_types import ReportType
from app.services.employee_sync import sync_employees_from_report_rows


logger = logging.getLogger(__name__)


def parse_shift_adherence_upload(db: Session, upload_id: UUID) -> dict[str, int]:
    upload_history = get_shift_adherence_upload(db=db, upload_id=upload_id)
    mark_upload_processing(db=db, upload_history=upload_history)
    total_records = 0
    processed_records = 0
    failed_records = 0

    try:
        raw_records = get_shift_adherence_raw_records(db=db, upload_id=upload_id)
        total_records = len(raw_records)
        adherence_rows, row_errors = map_shift_adherence_rows(
            raw_records, known_emp_ids=load_known_emp_ids(db)
        )
        for row in adherence_rows:
            row["upload_id"] = upload_id
        failed_records = len(row_errors)
        processed_records = total_records - failed_records

        upsert_agent_shift_adherence(db=db, adherence_rows=adherence_rows)
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
            detail="Shift adherence parser failed",
        ) from exc


def get_shift_adherence_upload(db: Session, upload_id: UUID) -> UploadHistory:
    upload_history = db.get(UploadHistory, upload_id)
    if upload_history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload history not found",
        )
    if upload_history.report_type != ReportType.SHIFT_ADHERENCE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload is not a SHIFT_ADHERENCE report",
        )
    return upload_history


def get_shift_adherence_raw_records(
    db: Session,
    upload_id: UUID,
) -> list[RawReportRecord]:
    statement = (
        select(RawReportRecord)
        .where(
            RawReportRecord.upload_id == upload_id,
            RawReportRecord.report_type == ReportType.SHIFT_ADHERENCE.value,
        )
        .order_by(RawReportRecord.row_number.asc())
    )
    return list(db.scalars(statement).all())


def map_shift_adherence_rows(
    raw_records: list[RawReportRecord],
    known_emp_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[RowError]]:
    adherence_rows: list[dict[str, Any]] = []
    row_errors: list[RowError] = []

    for raw_record in raw_records:
        try:
            row = map_shift_adherence_row(raw_record.raw_data)
            check_report_row(row, known_emp_ids=known_emp_ids)
            adherence_rows.append(row)
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Shift adherence row %s skipped: %s", raw_record.row_number, exc
            )
            row_errors.append((raw_record.row_number, str(exc)))

    return adherence_rows, row_errors


def map_shift_adherence_row(raw_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "emp_id": str(require_raw_value(raw_data=raw_data, column_name="Emp ID")),
        "employee_name": str(
            require_raw_value(raw_data=raw_data, column_name="Emp Name")
        ),
        "report_date": parse_date(
            require_raw_value(raw_data=raw_data, column_name="Date")
        ),
        "status": str(require_raw_value(raw_data=raw_data, column_name="Status")),
        "process": str(require_raw_value(raw_data=raw_data, column_name="Process")),
        "designation": str(
            require_raw_value(raw_data=raw_data, column_name="Designation")
        ),
        "manager_name": str(require_raw_value(raw_data=raw_data, column_name="Manager")),
        "attendance": str(
            require_raw_value(raw_data=raw_data, column_name="Attendance")
        ),
        "shift_start_time": parse_time(
            require_raw_value(raw_data=raw_data, column_name="Shift in")
        ),
        "shift_end_time": parse_time(
            require_raw_value(raw_data=raw_data, column_name="Shift out")
        ),
        "actual_login_time": parse_time(
            require_raw_value(raw_data=raw_data, column_name="Log In")
        ),
        "actual_logout_time": parse_time(
            require_raw_value(raw_data=raw_data, column_name="log out")
        ),
        "login_hours_seconds": time_to_seconds(
            require_raw_value(raw_data=raw_data, column_name="Login hours")
        ),
        "downtime_seconds": time_to_seconds(
            require_raw_value(raw_data=raw_data, column_name="Downtime")
        ),
        "login_plus_downtime_seconds": time_to_seconds(
            require_raw_value(raw_data=raw_data, column_name="Login + downtime")
        ),
        # Excel percent cells arrive as fractions (0.875), so use parse_percent.
        "shift_login_adherence_percent": parse_percent(
            get_raw_value(raw_data=raw_data, column_name="Shift adherence Log IN")
        ),
        "adherence_status": str(
            require_raw_value(raw_data=raw_data, column_name="Adhere")
        ),
        "late_login_minutes": duration_to_minutes(
            get_raw_value(raw_data=raw_data, column_name="Late login")
        ),
        "early_logout_minutes": duration_to_minutes(
            get_raw_value(raw_data=raw_data, column_name="early logout")
        ),
        "adherence_flag": parse_bool(
            get_raw_value(raw_data=raw_data, column_name="Adherence")
        ),
        "non_adherence_flag": parse_bool(
            get_raw_value(raw_data=raw_data, column_name="Non Adherence"),
            true_values={"1", "true", "yes", "y", "non adherence"},
            false_values={"0", "false", "no", "n", "adherence"},
        ),
        "non_adherence_percent": parse_percent(
            get_raw_value(raw_data=raw_data, column_name="Non Adherence %")
        ),
    }


def upsert_agent_shift_adherence(
    db: Session,
    adherence_rows: list[dict[str, Any]],
) -> None:
    if not adherence_rows:
        return

    latest_rows_by_key = {
        (row["emp_id"], row["report_date"]): row
        for row in adherence_rows
    }

    existing_records = {
        (record.emp_id, record.report_date): record
        for record in db.scalars(
            select(AgentShiftAdherence).where(
                AgentShiftAdherence.emp_id.in_({key[0] for key in latest_rows_by_key}),
                AgentShiftAdherence.report_date.in_(
                    {key[1] for key in latest_rows_by_key}
                ),
            )
        ).all()
    }

    for key, row in latest_rows_by_key.items():
        existing_record = existing_records.get(key)
        if existing_record is None:
            db.add(AgentShiftAdherence(**row))
            continue

        for field_name, value in row.items():
            setattr(existing_record, field_name, value)

    db.commit()
    # Every agent in a report should also be listed in Employee Master.
    sync_employees_from_report_rows(db, list(latest_rows_by_key.values()))
