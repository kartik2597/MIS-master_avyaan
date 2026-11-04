import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_shrinkage import AgentShrinkage
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
    get_raw_value,
    parse_date,
    parse_int,
    parse_percent,
    require_raw_value,
    time_to_seconds,
)
from app.reports.report_types import ReportType
from app.services.employee_sync import sync_employees_from_report_rows


logger = logging.getLogger(__name__)


def parse_shrinkage_upload(db: Session, upload_id: UUID) -> dict[str, int]:
    upload_history = get_shrinkage_upload(db=db, upload_id=upload_id)
    mark_upload_processing(db=db, upload_history=upload_history)
    total_records = 0
    processed_records = 0
    failed_records = 0

    try:
        raw_records = get_shrinkage_raw_records(db=db, upload_id=upload_id)
        total_records = len(raw_records)
        shrinkage_rows, row_errors = map_shrinkage_rows(
            raw_records, known_emp_ids=load_known_emp_ids(db)
        )
        for row in shrinkage_rows:
            row["upload_id"] = upload_id
        failed_records = len(row_errors)
        processed_records = total_records - failed_records

        upsert_agent_shrinkage(db=db, shrinkage_rows=shrinkage_rows)
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
            detail="Shrinkage parser failed",
        ) from exc


def get_shrinkage_upload(db: Session, upload_id: UUID) -> UploadHistory:
    upload_history = db.get(UploadHistory, upload_id)
    if upload_history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload history not found",
        )
    if upload_history.report_type != ReportType.SHRINKAGE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload is not a SHRINKAGE report",
        )
    return upload_history


def get_shrinkage_raw_records(
    db: Session,
    upload_id: UUID,
) -> list[RawReportRecord]:
    statement = (
        select(RawReportRecord)
        .where(
            RawReportRecord.upload_id == upload_id,
            RawReportRecord.report_type == ReportType.SHRINKAGE.value,
        )
        .order_by(RawReportRecord.row_number.asc())
    )
    return list(db.scalars(statement).all())


def map_shrinkage_rows(
    raw_records: list[RawReportRecord],
    known_emp_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[RowError]]:
    shrinkage_rows: list[dict[str, Any]] = []
    row_errors: list[RowError] = []

    for raw_record in raw_records:
        try:
            row = map_shrinkage_row(raw_record.raw_data)
            check_report_row(row, known_emp_ids=known_emp_ids)
            shrinkage_rows.append(row)
        except (TypeError, ValueError) as exc:
            logger.warning("Shrinkage row %s skipped: %s", raw_record.row_number, exc)
            row_errors.append((raw_record.row_number, str(exc)))

    return shrinkage_rows, row_errors


def map_shrinkage_row(raw_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_date": parse_date(
            require_raw_value(raw_data=raw_data, column_name="Date")
        ),
        "emp_id": str(require_raw_value(raw_data=raw_data, column_name="Emp ID")),
        "employee_name": str(
            require_raw_value(raw_data=raw_data, column_name="Emp Name")
        ),
        "status": str(require_raw_value(raw_data=raw_data, column_name="Status")),
        "process": str(require_raw_value(raw_data=raw_data, column_name="Process")),
        "designation": str(
            require_raw_value(raw_data=raw_data, column_name="Designation")
        ),
        "manager_name": str(require_raw_value(raw_data=raw_data, column_name="Manager")),
        "date_of_joining": parse_date(
            require_raw_value(raw_data=raw_data, column_name="DOS")
        ),
        "login_hours_seconds": time_to_seconds(
            require_raw_value(raw_data=raw_data, column_name="Login hours")
        ),
        "attendance": str(
            require_raw_value(raw_data=raw_data, column_name="Attendance")
        ),
        "employee_age_days": parse_int(
            require_raw_value(raw_data=raw_data, column_name="Age")
        ),
        "tenure_bucket": str(require_raw_value(raw_data=raw_data, column_name="Bucket")),
        "agent_count": parse_int(
            get_raw_value(raw_data=raw_data, column_name="Agent count")
        ),
        "present_count": parse_int(get_raw_value(raw_data=raw_data, column_name="P")),
        "absent_count": parse_int(get_raw_value(raw_data=raw_data, column_name="A")),
        "lwp_count": parse_int(get_raw_value(raw_data=raw_data, column_name="LWP")),
        "cl_count": parse_int(get_raw_value(raw_data=raw_data, column_name="CL")),
        "half_day_count": parse_int(get_raw_value(raw_data=raw_data, column_name="HD")),
        "training_count": parse_int(get_raw_value(raw_data=raw_data, column_name="TP")),
        # Excel percent cells arrive as fractions (0.125 for 12.5%), so use
        # parse_percent; parse_decimal would store them 100x too small.
        "planned_shrinkage": parse_percent(
            get_raw_value(raw_data=raw_data, column_name="Planned Shrinkage")
        ),
        "unplanned_shrinkage": parse_percent(
            get_raw_value(raw_data=raw_data, column_name="Unplanned Shrinkage")
        ),
        "opening_headcount": parse_int(
            get_raw_value(raw_data=raw_data, column_name="Opening")
        ),
        "closing_headcount": parse_int(
            get_raw_value(raw_data=raw_data, column_name="Closing")
        ),
        "attrition": parse_int(
            get_raw_value(raw_data=raw_data, column_name="Attrition")
        ),
    }


def upsert_agent_shrinkage(
    db: Session,
    shrinkage_rows: list[dict[str, Any]],
) -> None:
    if not shrinkage_rows:
        return

    latest_rows_by_key = {
        (row["emp_id"], row["report_date"]): row
        for row in shrinkage_rows
    }

    existing_records = {
        (record.emp_id, record.report_date): record
        for record in db.scalars(
            select(AgentShrinkage).where(
                AgentShrinkage.emp_id.in_({key[0] for key in latest_rows_by_key}),
                AgentShrinkage.report_date.in_(
                    {key[1] for key in latest_rows_by_key}
                ),
            )
        ).all()
    }

    for key, row in latest_rows_by_key.items():
        existing_record = existing_records.get(key)
        if existing_record is None:
            db.add(AgentShrinkage(**row))
            continue

        for field_name, value in row.items():
            setattr(existing_record, field_name, value)

    db.commit()
    # Every agent in a report should also be listed in Employee Master.
    sync_employees_from_report_rows(db, list(latest_rows_by_key.values()))
