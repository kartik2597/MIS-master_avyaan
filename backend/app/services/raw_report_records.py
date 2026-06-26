from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.raw_report_record import RawReportRecord


def save_raw_report_rows(
    db: Session,
    *,
    upload_id: UUID,
    report_type: str,
    rows: Iterable[dict[str, Any]],
) -> list[RawReportRecord]:
    raw_records = [
        RawReportRecord(
            upload_id=upload_id,
            report_type=report_type,
            row_number=row_number,
            raw_data=row,
        )
        for row_number, row in enumerate(rows, start=1)
    ]

    if not raw_records:
        return []

    db.add_all(raw_records)
    db.commit()

    for raw_record in raw_records:
        db.refresh(raw_record)

    return raw_records


def get_raw_rows(db: Session, upload_id: UUID) -> list[RawReportRecord]:
    statement = (
        select(RawReportRecord)
        .where(RawReportRecord.upload_id == upload_id)
        .order_by(RawReportRecord.row_number.asc())
    )
    return list(db.scalars(statement).all())

