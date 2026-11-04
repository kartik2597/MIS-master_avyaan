import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_daily_performance import AgentDailyPerformance
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


def parse_apr_upload(db: Session, upload_id: UUID) -> dict[str, int]:
    upload_history = get_apr_upload(db=db, upload_id=upload_id)
    mark_upload_processing(db=db, upload_history=upload_history)
    total_records = 0
    processed_records = 0
    failed_records = 0

    try:
        raw_records = get_apr_raw_records(db=db, upload_id=upload_id)
        total_records = len(raw_records)
        performance_rows, row_errors = map_apr_rows(
            raw_records, known_emp_ids=load_known_emp_ids(db)
        )
        for row in performance_rows:
            row["upload_id"] = upload_id
        failed_records = len(row_errors)
        processed_records = total_records - failed_records

        upsert_agent_daily_performance(db=db, performance_rows=performance_rows)
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
            detail="APR parser failed",
        ) from exc


def get_apr_upload(db: Session, upload_id: UUID) -> UploadHistory:
    upload_history = db.get(UploadHistory, upload_id)
    if upload_history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload history not found",
        )
    if upload_history.report_type != ReportType.APR.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload is not an APR report",
        )
    return upload_history


def get_apr_raw_records(db: Session, upload_id: UUID) -> list[RawReportRecord]:
    statement = (
        select(RawReportRecord)
        .where(
            RawReportRecord.upload_id == upload_id,
            RawReportRecord.report_type == ReportType.APR.value,
        )
        .order_by(RawReportRecord.row_number.asc())
    )
    return list(db.scalars(statement).all())


def map_apr_rows(
    raw_records: list[RawReportRecord],
    known_emp_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[RowError]]:
    performance_rows: list[dict[str, Any]] = []
    row_errors: list[RowError] = []

    for raw_record in raw_records:
        try:
            row = map_apr_row(raw_record.raw_data)
            check_report_row(row, known_emp_ids=known_emp_ids)
            performance_rows.append(row)
        except (TypeError, ValueError) as exc:
            logger.warning("APR row %s skipped: %s", raw_record.row_number, exc)
            row_errors.append((raw_record.row_number, str(exc)))

    return performance_rows, row_errors


def map_apr_row(raw_data: dict[str, Any]) -> dict[str, Any]:
    staff_time_seconds = time_to_seconds(
        require_raw_value(raw_data=raw_data, column_name="Staff time")
    )
    talk_time_seconds = time_to_seconds(
        require_raw_value(raw_data=raw_data, column_name="Total Talk Time")
    )
    break_time_seconds = time_to_seconds(
        require_raw_value(raw_data=raw_data, column_name="Total Break Time")
    )
    idle_time_seconds = time_to_seconds(
        require_raw_value(raw_data=raw_data, column_name="Total Idle Time")
    )

    connected_calls = parse_int(
        get_raw_value(raw_data=raw_data, column_name="Connected")
    )
    positive_calls = parse_int(
        get_raw_value(raw_data=raw_data, column_name="Positive")
    )

    return {
        "emp_id": str(require_raw_value(raw_data=raw_data, column_name="Agent ID")),
        "employee_name": str(
            require_raw_value(raw_data=raw_data, column_name="Agent Name")
        ),
        "report_date": parse_date(
            require_raw_value(raw_data=raw_data, column_name="Date Time")
        ),
        "campaign": str(require_raw_value(raw_data=raw_data, column_name="Campaigns")),
        "user_group": str(
            require_raw_value(raw_data=raw_data, column_name="User Group")
        ),
        "attendance": str(
            require_raw_value(raw_data=raw_data, column_name="Attendance")
        ),
        # The APR report has no login column. The column is NOT NULL, so store 0
        # instead of a copy of staff time that could be mistaken for real login time.
        # Login time comes from the shift adherence report (login_hours_seconds).
        "login_hours": 0,
        "staff_time": staff_time_seconds,
        "talk_time": talk_time_seconds,
        "break_time": break_time_seconds,
        "idle_time": idle_time_seconds,
        "productivity_percent": parse_percent(
            get_raw_value(raw_data=raw_data, column_name="Productivity %")
        ),
        "total_calls": parse_int(
            get_raw_value(raw_data=raw_data, column_name="Total Calls")
        ),
        "dialer_total_calls": parse_int(
            get_raw_value(raw_data=raw_data, column_name="Total Calls")
        ),
        "dialflow_total_calls": parse_dialflow_total_calls(raw_data),
        "connected_calls": connected_calls,
        "not_connected_calls": parse_int(
            get_raw_value(raw_data=raw_data, column_name="Not Connected")
        ),
        "positive_calls": positive_calls,
        "conversion_percent": calculate_conversion_percent(
            positive_calls=positive_calls, connected_calls=connected_calls
        ),
        "tl_remark": str(
            get_raw_value(raw_data=raw_data, column_name="TL Remark") or ""
        ),
    }


def calculate_conversion_percent(*, positive_calls: int, connected_calls: int) -> Decimal:
    """Conversion = positive calls as a percentage of connected calls.

    The APR report has no conversion column, so it is worked out from the call
    counts. With no connected calls there is nothing to convert, so it is 0.
    """
    if connected_calls <= 0:
        return Decimal("0")
    percent = Decimal(positive_calls) * 100 / Decimal(connected_calls)
    return percent.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_dialflow_total_calls(raw_data: dict[str, Any]) -> int:
    """Read the dialflow call count from a distinct "Total calls" column.

    Column lookup ignores case, so "Total Calls" and "Total calls" would resolve
    to the same column. Only use the dialflow value when the file really has
    both columns; otherwise there is no separate dialflow figure.
    """
    if "Total calls" in raw_data and "Total Calls" in raw_data:
        return parse_int(raw_data.get("Total calls"))
    return 0


def upsert_agent_daily_performance(
    db: Session,
    performance_rows: list[dict[str, Any]],
) -> None:
    if not performance_rows:
        return

    # An agent can work several campaigns in a day, so campaign is part of the key.
    latest_rows_by_key = {
        (row["emp_id"], row["report_date"], row["campaign"]): row
        for row in performance_rows
    }

    existing_records = {
        (record.emp_id, record.report_date, record.campaign): record
        for record in db.scalars(
            select(AgentDailyPerformance).where(
                AgentDailyPerformance.emp_id.in_({key[0] for key in latest_rows_by_key}),
                AgentDailyPerformance.report_date.in_(
                    {key[1] for key in latest_rows_by_key}
                ),
            )
        ).all()
    }

    for key, row in latest_rows_by_key.items():
        existing_record = existing_records.get(key)
        if existing_record is None:
            db.add(AgentDailyPerformance(**row))
            continue

        for field_name, value in row.items():
            setattr(existing_record, field_name, value)

    db.commit()
    # Every agent in a report should also be listed in Employee Master.
    sync_employees_from_report_rows(db, list(latest_rows_by_key.values()))
