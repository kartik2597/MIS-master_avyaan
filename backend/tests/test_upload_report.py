"""The uploads and data-quality section of the daily/weekly/monthly report."""

from datetime import date, datetime
from io import BytesIO

import pytest
from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.upload_history import UploadHistory
from app.models.user import UserRole
from app.services.report_export import (
    REPORT_SECTIONS,
    build_report_data,
    render_report,
    summary_blocks,
)


def _upload(user_id, name, status, uploaded_at, *, processed=0, failed=0, message=None):
    return UploadHistory(
        file_name=f"stored_{name}",
        original_file_name=name,
        report_type="APR",
        file_size=100,
        uploaded_by=user_id,
        upload_status=status,
        total_records=processed + failed,
        processed_records=processed,
        failed_records=failed,
        error_message=message,
        uploaded_at=uploaded_at,
    )


@pytest.fixture()
def seeded(engine, make_user):
    user = make_user(role=UserRole.MIS)
    with Session(engine) as session:
        session.add_all(
            [
                _upload(user.id, "ok.xlsx", "COMPLETED", datetime(2026, 11, 2, 10, 0), processed=50),
                _upload(
                    user.id, "partial.xlsx", "COMPLETED", datetime(2026, 11, 3, 9, 0),
                    processed=48, failed=2, message="2 row(s) skipped. row 5: bad date",
                ),
                _upload(
                    user.id, "broken.xlsx", "FAILED", datetime(2026, 11, 3, 15, 30),
                    message="Missing required columns",
                ),
                # Outside the period, must not be counted.
                _upload(user.id, "old.xlsx", "COMPLETED", datetime(2026, 10, 1, 8, 0), processed=10),
            ]
        )
        session.commit()
    return engine


def test_uploads_is_a_default_report_section():
    assert "uploads" in REPORT_SECTIONS


def test_uploads_section_counts_and_lists_problems(seeded):
    with Session(seeded) as db:
        data = build_report_data(
            db, "weekly", date(2026, 11, 2), date(2026, 11, 5), sections=["uploads"]
        )

    report = data.uploads
    assert report is not None
    assert (report.total, report.completed, report.failed) == (3, 2, 1)
    assert report.with_skipped_rows == 1
    assert (report.rows_processed, report.rows_skipped) == (98, 2)
    assert [issue.file_name for issue in report.issues] == ["partial.xlsx", "broken.xlsx"]
    assert report.days_without_upload == [date(2026, 11, 4), date(2026, 11, 5)]
    assert report.by_type[0].report_type == "APR"
    assert report.by_type[0].uploads == 3


def test_team_scoped_report_leaves_uploads_out(seeded):
    with Session(seeded) as db:
        data = build_report_data(
            db,
            "daily",
            date(2026, 11, 2),
            date(2026, 11, 2),
            scope=select(Employee),
            sections=["uploads"],
        )

    assert data.uploads is None
    assert summary_blocks(data) == []


def test_excel_report_has_upload_sheets(seeded):
    with Session(seeded) as db:
        data = build_report_data(
            db, "weekly", date(2026, 11, 2), date(2026, 11, 5), sections=["uploads"]
        )

    workbook = load_workbook(BytesIO(render_report(data, "xlsx")))
    assert {"Summary", "Uploads by type", "Upload issues", "Days with no upload"} <= set(
        workbook.sheetnames
    )
    summary_text = " ".join(
        str(cell.value) for row in workbook["Summary"].iter_rows() for cell in row if cell.value
    )
    assert "1 upload(s) failed" in summary_text


def test_pdf_report_renders_with_uploads(seeded):
    pytest.importorskip("reportlab")
    with Session(seeded) as db:
        data = build_report_data(
            db, "weekly", date(2026, 11, 2), date(2026, 11, 5), sections=["uploads"]
        )

    assert render_report(data, "pdf").startswith(b"%PDF")
