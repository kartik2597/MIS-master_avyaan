"""Shared upload-status helpers used by every importer and parser.

Each importer used to carry its own copy of these functions. Keep the status
names and the "row failed" summary in one place so they cannot drift apart.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.upload_history import UploadHistory


UPLOAD_STATUS_PROCESSING = "PROCESSING"
UPLOAD_STATUS_COMPLETED = "COMPLETED"
UPLOAD_STATUS_FAILED = "FAILED"

MAX_ERROR_MESSAGE_LENGTH = 1000
MAX_ROW_ERRORS_IN_MESSAGE = 10
# How many skipped rows are kept in full for the Validation Report page.
MAX_STORED_ROW_ERRORS = 1000

# (row number in the file, reason the row was skipped)
RowError = tuple[int, str]


def serialize_row_errors(row_errors: list[RowError]) -> list[dict[str, object]] | None:
    """Row errors as JSON-friendly dicts, capped. None when there are none."""
    if not row_errors:
        return None
    return [
        {"row": row_number, "reason": str(reason)[:500]}
        for row_number, reason in row_errors[:MAX_STORED_ROW_ERRORS]
    ]


def summarize_row_errors(row_errors: list[RowError], failed_records: int) -> str | None:
    """Short text listing the first few skipped rows and why.

    Returns None when nothing failed, so a clean import keeps an empty message.
    """
    if failed_records <= 0:
        return None

    shown = row_errors[:MAX_ROW_ERRORS_IN_MESSAGE]
    details = "; ".join(f"row {row_number}: {reason}" for row_number, reason in shown)
    summary = f"{failed_records} row(s) skipped"
    if details:
        summary += f". {details}"
    hidden = len(row_errors) - len(shown)
    if hidden > 0:
        summary += f"; and {hidden} more"
    return summary[:MAX_ERROR_MESSAGE_LENGTH]


def mark_upload_processing(db: Session, upload_history: UploadHistory) -> None:
    upload_history.upload_status = UPLOAD_STATUS_PROCESSING
    upload_history.processing_started_at = datetime.now()
    upload_history.processing_completed_at = None
    upload_history.error_message = None
    upload_history.row_errors = None
    db.commit()
    db.refresh(upload_history)


def mark_upload_completed(
    db: Session,
    *,
    upload_history: UploadHistory,
    total_records: int,
    processed_records: int,
    failed_records: int,
    row_errors: list[RowError] | None = None,
) -> None:
    upload_history.upload_status = UPLOAD_STATUS_COMPLETED
    upload_history.total_records = total_records
    upload_history.processed_records = processed_records
    upload_history.failed_records = failed_records
    upload_history.processing_completed_at = datetime.now()
    upload_history.error_message = summarize_row_errors(row_errors or [], failed_records)
    upload_history.row_errors = serialize_row_errors(row_errors or [])
    db.commit()


def mark_upload_failed(
    db: Session,
    *,
    upload_history: UploadHistory,
    error_message: str,
    total_records: int | None = None,
    processed_records: int | None = None,
    failed_records: int | None = None,
) -> None:
    upload_history.upload_status = UPLOAD_STATUS_FAILED
    if total_records is not None:
        upload_history.total_records = total_records
    if processed_records is not None:
        upload_history.processed_records = processed_records
    if failed_records is not None:
        upload_history.failed_records = failed_records
    upload_history.processing_completed_at = datetime.now()
    upload_history.error_message = error_message[:MAX_ERROR_MESSAGE_LENGTH]
    db.commit()
