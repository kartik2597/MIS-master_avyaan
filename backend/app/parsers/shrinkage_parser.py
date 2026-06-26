from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_shrinkage import AgentShrinkage
from app.models.raw_report_record import RawReportRecord
from app.models.upload_history import UploadHistory
from app.parsers.utils import (
    get_raw_value,
    parse_date,
    parse_decimal,
    parse_int,
    require_raw_value,
    time_to_seconds,
)
from app.reports.report_types import ReportType


UPLOAD_STATUS_PROCESSING = "PROCESSING"
UPLOAD_STATUS_COMPLETED = "COMPLETED"
UPLOAD_STATUS_FAILED = "FAILED"


def parse_shrinkage_upload(db: Session, upload_id: UUID) -> dict[str, int]:
    upload_history = get_shrinkage_upload(db=db, upload_id=upload_id)
    mark_upload_processing(db=db, upload_history=upload_history)
    total_records = 0
    processed_records = 0
    failed_records = 0

    try:
        raw_records = get_shrinkage_raw_records(db=db, upload_id=upload_id)
        total_records = len(raw_records)
        shrinkage_rows, failed_records = map_shrinkage_rows(raw_records)
        processed_records = total_records - failed_records

        upsert_agent_shrinkage(db=db, shrinkage_rows=shrinkage_rows)
        mark_upload_completed(
            db=db,
            upload_history=upload_history,
            total_records=total_records,
            processed_records=processed_records,
            failed_records=failed_records,
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
) -> tuple[list[dict[str, Any]], int]:
    shrinkage_rows: list[dict[str, Any]] = []
    failed_records = 0

    for raw_record in raw_records:
        try:
            shrinkage_rows.append(map_shrinkage_row(raw_record.raw_data))
        except (TypeError, ValueError):
            failed_records += 1

    return shrinkage_rows, failed_records


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
        "planned_shrinkage": parse_decimal(
            get_raw_value(raw_data=raw_data, column_name="Planned Shrinkage")
        ),
        "unplanned_shrinkage": parse_decimal(
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

    for row in latest_rows_by_key.values():
        existing_record = db.scalar(
            select(AgentShrinkage).where(
                AgentShrinkage.emp_id == row["emp_id"],
                AgentShrinkage.report_date == row["report_date"],
            )
        )
        if existing_record is None:
            db.add(AgentShrinkage(**row))
            continue

        for field_name, value in row.items():
            setattr(existing_record, field_name, value)

    db.commit()


def mark_upload_processing(db: Session, upload_history: UploadHistory) -> None:
    upload_history.upload_status = UPLOAD_STATUS_PROCESSING
    upload_history.processing_started_at = datetime.now()
    upload_history.processing_completed_at = None
    upload_history.error_message = None
    db.commit()
    db.refresh(upload_history)


def mark_upload_completed(
    db: Session,
    *,
    upload_history: UploadHistory,
    total_records: int,
    processed_records: int,
    failed_records: int,
) -> None:
    upload_history.upload_status = UPLOAD_STATUS_COMPLETED
    upload_history.total_records = total_records
    upload_history.processed_records = processed_records
    upload_history.failed_records = failed_records
    upload_history.processing_completed_at = datetime.now()
    upload_history.error_message = None
    db.commit()


def mark_upload_failed(
    db: Session,
    *,
    upload_history: UploadHistory,
    total_records: int,
    processed_records: int,
    failed_records: int,
    error_message: str,
) -> None:
    upload_history.upload_status = UPLOAD_STATUS_FAILED
    upload_history.total_records = total_records
    upload_history.processed_records = processed_records
    upload_history.failed_records = failed_records
    upload_history.processing_completed_at = datetime.now()
    upload_history.error_message = error_message[:1000]
    db.commit()
