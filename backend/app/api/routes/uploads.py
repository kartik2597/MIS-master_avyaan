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
    SheetUploadResult,
    UploadHistoryList,
    UploadHistoryRead,
    UploadValidationReport,
)
from app.services.file_upload import upload_and_detect_workbook
from app.services.upload_report import build_validation_report
from app.services.upload_history import (
    delete_upload_history,
    get_upload_history_or_404,
    list_upload_history,
)


router = APIRouter()

VIEW_ROLES = [UserRole.ADMIN, UserRole.MIS, UserRole.MANAGER, UserRole.TL]
# Everyone who can upload can delete. ADMIN and MIS can delete any upload; the
# other roles can only reach (and so only delete) their own, because
# get_upload_history_or_404 hides other people's uploads from them.
DELETE_ROLES = VIEW_ROLES


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
    outcome = upload_and_detect_workbook(
        db=db,
        upload_file=file,
        uploaded_by=current_user,
    )
    sheets = [
        SheetUploadResult(
            upload_id=sheet.upload_history.id,
            sheet_name=sheet.sheet_name,
            detected_report_type=sheet.detection.detected_report_type,
            confidence_score=sheet.detection.confidence_score,
            total_columns=sheet.total_columns,
            total_records=sheet.upload_history.total_records,
            missing_columns=sheet.validation_result.missing_columns,
        )
        for sheet in outcome.sheets
    ]
    first = sheets[0]
    return FileUploadDetectionResponse(
        upload_id=first.upload_id,
        file_name=outcome.sheets[0].upload_history.file_name,
        detected_report_type=first.detected_report_type,
        confidence_score=first.confidence_score,
        total_columns=first.total_columns,
        missing_columns=first.missing_columns,
        sheets=sheets,
        ignored_sheets=outcome.ignored_sheets,
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


@router.get(
    "/{upload_id}/validation",
    response_model=UploadValidationReport,
    dependencies=[Depends(require_role(VIEW_ROLES))],
)
def read_upload_validation_report(
    upload_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UploadValidationReport:
    """Column problems and every skipped row ("row 45: invalid date") for one upload."""
    upload = get_upload_history_or_404(
        db=db,
        upload_id=upload_id,
        current_user=current_user,
    )
    return build_validation_report(upload)


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
