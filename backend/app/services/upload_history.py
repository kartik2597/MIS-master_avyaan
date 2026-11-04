from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, and_, case, delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.agent_daily_performance import AgentDailyPerformance
from app.models.agent_shift_adherence import AgentShiftAdherence
from app.models.agent_shrinkage import AgentShrinkage
from app.models.employee import Employee
from app.models.raw_report_record import RawReportRecord
from app.models.upload_history import UploadHistory
from app.models.user import User, UserRole
from app.services.file_upload import build_upload_directory


def can_view_all_uploads(user: User) -> bool:
    return user.role in {UserRole.ADMIN, UserRole.MIS}


def get_upload_history_or_404(
    db: Session,
    upload_id: UUID,
    current_user: User,
) -> UploadHistory:
    statement = select(UploadHistory).where(UploadHistory.id == upload_id)
    if not can_view_all_uploads(current_user):
        statement = statement.where(UploadHistory.uploaded_by == current_user.id)

    upload = db.scalar(statement)
    if upload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload history not found",
        )
    return upload


# Statuses that mean the whole upload failed.
FAILED_STATUSES = ("FAILED", "VALIDATION_FAILED")


def has_issues_clause():
    """An upload with a problem: it failed, or it imported but skipped some rows."""
    return or_(
        UploadHistory.upload_status.in_(FAILED_STATUSES),
        UploadHistory.failed_records > 0,
    )


def apply_upload_filters(
    statement: Select[tuple[UploadHistory]],
    *,
    current_user: User,
    report_type: str | None = None,
    upload_status: str | None = None,
    uploaded_by: UUID | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    has_issues: bool | None = None,
) -> Select[tuple[UploadHistory]]:
    if can_view_all_uploads(current_user):
        if uploaded_by:
            statement = statement.where(UploadHistory.uploaded_by == uploaded_by)
    else:
        statement = statement.where(UploadHistory.uploaded_by == current_user.id)

    if report_type:
        statement = statement.where(UploadHistory.report_type == report_type)
    if upload_status:
        statement = statement.where(UploadHistory.upload_status == upload_status)

    term = (search or "").strip()
    if term:
        # Escape LIKE wildcards so typing "%" or "_" searches for the character.
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        statement = statement.where(
            UploadHistory.original_file_name.ilike(f"%{escaped}%", escape="\\")
        )

    if date_from:
        statement = statement.where(func.date(UploadHistory.uploaded_at) >= date_from)
    if date_to:
        statement = statement.where(func.date(UploadHistory.uploaded_at) <= date_to)

    if has_issues is True:
        statement = statement.where(has_issues_clause())
    elif has_issues is False:
        statement = statement.where(~has_issues_clause())

    return statement


def list_upload_history(
    db: Session,
    *,
    current_user: User,
    page: int,
    page_size: int,
    report_type: str | None = None,
    upload_status: str | None = None,
    uploaded_by: UUID | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    has_issues: bool | None = None,
) -> tuple[list[UploadHistory], int]:
    filtered_statement = apply_upload_filters(
        select(UploadHistory),
        current_user=current_user,
        report_type=report_type,
        upload_status=upload_status,
        uploaded_by=uploaded_by,
        search=search,
        date_from=date_from,
        date_to=date_to,
        has_issues=has_issues,
    )

    total = db.scalar(
        select(func.count()).select_from(filtered_statement.subquery())
    ) or 0
    uploads = db.scalars(
        filtered_statement
        .options(selectinload(UploadHistory.uploader))
        .order_by(UploadHistory.uploaded_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return list(uploads), total


def get_upload_summary(db: Session, *, current_user: User) -> dict[str, int]:
    """Counts over every upload the viewer may see, for the KPI cards and sidebar badge."""
    visible = []
    if not can_view_all_uploads(current_user):
        visible.append(UploadHistory.uploaded_by == current_user.id)

    issue = has_issues_clause()
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    def count_where(condition):
        return func.coalesce(func.sum(case((condition, 1), else_=0)), 0)

    row = db.execute(
        select(
            func.count(),
            count_where(UploadHistory.upload_status == "COMPLETED"),
            count_where(UploadHistory.upload_status.in_(FAILED_STATUSES)),
            count_where(UploadHistory.upload_status == "PROCESSING"),
            count_where(issue),
            count_where(and_(issue, UploadHistory.uploaded_at >= week_ago)),
        ).where(*visible)
    ).one()

    return {
        "total": int(row[0] or 0),
        "completed": int(row[1] or 0),
        "failed": int(row[2] or 0),
        "processing": int(row[3] or 0),
        "with_issues": int(row[4] or 0),
        "recent_issues": int(row[5] or 0),
    }


def remove_stored_upload_file(file_name: str, uploaded_at) -> None:
    expected_path = build_upload_directory(uploaded_at) / file_name
    if expected_path.exists():
        expected_path.unlink(missing_ok=True)
        return

    # The dated folder can differ from the DB timestamp (timezone, midnight).
    uploads_root = settings.STORAGE_PATH / "uploads"
    if uploads_root.exists():
        for match in uploads_root.rglob(file_name):
            match.unlink(missing_ok=True)


# Every table an upload can write into. Rows are linked back by upload_id.
UPLOAD_DATA_MODELS = (
    RawReportRecord,
    AgentDailyPerformance,
    AgentShiftAdherence,
    AgentShrinkage,
    Employee,
)


def delete_upload_history(db: Session, upload: UploadHistory) -> None:
    file_name = upload.file_name
    uploaded_at = upload.uploaded_at
    upload_id = upload.id

    try:
        # One transaction: either the upload and all the data it created are
        # removed, or nothing is.
        for model in UPLOAD_DATA_MODELS:
            db.execute(delete(model).where(model.upload_id == upload_id))
        db.delete(upload)
        db.commit()
    except Exception:
        db.rollback()
        raise

    # Several uploads can share one stored file (one per sheet of a workbook), so
    # remove it only once no remaining upload points at it.
    still_used = db.scalar(
        select(func.count())
        .select_from(UploadHistory)
        .where(UploadHistory.file_name == file_name)
    )
    if not still_used:
        remove_stored_upload_file(file_name, uploaded_at)

