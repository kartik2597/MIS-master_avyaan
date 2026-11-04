"""Link report rows imported BEFORE migration 0012 back to their uploads.

Run once, after `alembic upgrade head`:

    python backfill_upload_ids.py            # preview only, changes nothing
    python backfill_upload_ids.py --apply    # write the changes

For each upload still in the history it re-maps the stored raw rows, finds the
matching report rows that have no upload_id yet, and sets it. Uploads are
processed oldest first, so when two uploads covered the same agent and date the
newest one ends up owning the row (the same rule the importers use).

Rows that match no remaining upload (for example the upload was already deleted
under the old behaviour) are only counted here. Remove them afterwards with:

    python clean_report_data.py --unlinked --apply
"""
import argparse
from collections import Counter

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.agent_daily_performance import AgentDailyPerformance
from app.models.agent_shift_adherence import AgentShiftAdherence
from app.models.agent_shrinkage import AgentShrinkage
from app.models.raw_report_record import RawReportRecord
from app.models.upload_history import UploadHistory
from app.parsers.apr_parser import map_apr_rows
from app.parsers.shift_adherence_parser import map_shift_adherence_rows
from app.parsers.shrinkage_parser import map_shrinkage_rows
from app.reports.report_types import ReportType


def key_apr(row):
    return (row["emp_id"], row["report_date"], row["campaign"])


def key_daily(row):
    return (row["emp_id"], row["report_date"])


# report type -> (mapper, model, key of a mapped row, key of a database row)
CONFIG = {
    ReportType.APR.value: (
        map_apr_rows,
        AgentDailyPerformance,
        key_apr,
        lambda r: (r.emp_id, r.report_date, r.campaign),
    ),
    ReportType.SHIFT_ADHERENCE.value: (
        map_shift_adherence_rows,
        AgentShiftAdherence,
        key_daily,
        lambda r: (r.emp_id, r.report_date),
    ),
    ReportType.SHRINKAGE.value: (
        map_shrinkage_rows,
        AgentShrinkage,
        key_daily,
        lambda r: (r.emp_id, r.report_date),
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write the changes")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        for report_type, (mapper, model, mapped_key, row_key) in CONFIG.items():
            unlinked = {
                row_key(record): record
                for record in db.scalars(
                    select(model).where(model.upload_id.is_(None))
                ).all()
            }
            total_unlinked = len(unlinked)
            if not unlinked:
                print(f"{report_type}: nothing to link")
                continue

            uploads = db.scalars(
                select(UploadHistory)
                .where(UploadHistory.report_type == report_type)
                .order_by(UploadHistory.uploaded_at.asc())
            ).all()

            linked = 0
            per_upload: Counter = Counter()
            owner: dict = {}
            for upload in uploads:
                raw_records = db.scalars(
                    select(RawReportRecord)
                    .where(
                        RawReportRecord.upload_id == upload.id,
                        RawReportRecord.report_type == report_type,
                    )
                    .order_by(RawReportRecord.row_number.asc())
                ).all()
                mapped_rows, _errors = mapper(list(raw_records))
                for mapped in mapped_rows:
                    key = mapped_key(mapped)
                    if key in unlinked:
                        owner[key] = upload.id  # later uploads overwrite earlier

            for key, upload_id in owner.items():
                unlinked[key].upload_id = upload_id
                per_upload[upload_id] += 1
                linked += 1

            orphans = [rec for key, rec in unlinked.items() if key not in owner]
            print(
                f"{report_type}: {total_unlinked} unlinked rows, "
                f"{linked} matched to {len(per_upload)} upload(s), "
                f"{len(orphans)} orphan(s)"
            )

        if args.apply:
            db.commit()
            print("Changes saved.")
        else:
            db.rollback()
            print("Preview only. Nothing was changed. Re-run with --apply to save.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
