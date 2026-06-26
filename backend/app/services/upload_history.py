from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.upload_history import UploadHistory
from app.models.user import User, UserRole


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


def apply_upload_filters(
    statement: Select[tuple[UploadHistory]],
    *,
    current_user: User,
    report_type: str | None = None,
    upload_status: str | None = None,
    uploaded_by: UUID | None = None,
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
) -> tuple[list[UploadHistory], int]:
    filtered_statement = apply_upload_filters(
        select(UploadHistory),
        current_user=current_user,
        report_type=report_type,
        upload_status=upload_status,
        uploaded_by=uploaded_by,
    )

    total = db.scalar(
        select(func.count()).select_from(filtered_statement.subquery())
    ) or 0
    uploads = db.scalars(
        filtered_statement
        .order_by(UploadHistory.uploaded_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return list(uploads), total


def delete_upload_history(db: Session, upload: UploadHistory) -> None:
    db.delete(upload)
    db.commit()

