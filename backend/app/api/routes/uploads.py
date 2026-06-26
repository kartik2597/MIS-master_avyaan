from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.database.session import get_db
from app.models.upload_history import UploadHistory
from app.models.user import User, UserRole
from app.schemas.upload_history import (
    FileUploadDetectionResponse,
    UploadHistoryList,
    UploadHistoryRead,
)
from app.services.file_upload import upload_and_detect_report
from app.services.upload_history import (
    delete_upload_history,
    get_upload_history_or_404,
    list_upload_history,
)


router = APIRouter()

VIEW_ROLES = [UserRole.ADMIN, UserRole.MIS, UserRole.MANAGER, UserRole.TL]
DELETE_ROLES = [UserRole.ADMIN, UserRole.MIS]


@router.post(
    "/file",
    response_model=FileUploadDetectionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(VIEW_ROLES))],
)
def upload_file_for_detection(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileUploadDetectionResponse:
    upload_history, detection, validation_result, total_columns = upload_and_detect_report(
        db=db,
        upload_file=file,
        uploaded_by=current_user,
    )
    return FileUploadDetectionResponse(
        upload_id=upload_history.id,
        file_name=upload_history.file_name,
        detected_report_type=detection.detected_report_type,
        confidence_score=detection.confidence_score,
        total_columns=total_columns,
        missing_columns=validation_result.missing_columns,
    )


@router.get(
    "",
    response_model=UploadHistoryList,
    dependencies=[Depends(require_role(VIEW_ROLES))],
)
def read_upload_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    report_type: str | None = None,
    upload_status: str | None = None,
    uploaded_by: UUID | None = None,
) -> UploadHistoryList:
    uploads, total = list_upload_history(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        report_type=report_type,
        upload_status=upload_status,
        uploaded_by=uploaded_by,
    )
    return UploadHistoryList(items=uploads, total=total, page=page, page_size=page_size)


@router.get(
    "/{upload_id}",
    response_model=UploadHistoryRead,
    dependencies=[Depends(require_role(VIEW_ROLES))],
)
def read_upload_history_record(
    upload_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UploadHistory:
    return get_upload_history_or_404(
        db=db,
        upload_id=upload_id,
        current_user=current_user,
    )


@router.delete(
    "/{upload_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(DELETE_ROLES))],
)
def delete_upload_history_record(
    upload_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    upload = get_upload_history_or_404(
        db=db,
        upload_id=upload_id,
        current_user=current_user,
    )
    delete_upload_history(db=db, upload=upload)
