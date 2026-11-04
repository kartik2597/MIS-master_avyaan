from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.database.session import get_db
from app.imports import import_master_database
from app.models.upload_history import UploadHistory
from app.models.user import UserRole
from app.parsers.apr_parser import parse_apr_upload
from app.parsers.shift_adherence_parser import parse_shift_adherence_upload
from app.parsers.shrinkage_parser import parse_shrinkage_upload
from app.parsers.workbook_parsers import (
    parse_daily_activity_upload,
    parse_employee_roster_upload,
    parse_shrinkage_hours_upload,
)
from app.reports.report_types import ReportType
from app.schemas.imports import ImportSummary
from app.services.file_upload import is_importable


router = APIRouter()

IMPORT_ROLES = [UserRole.ADMIN, UserRole.MIS]

# Report types that have a parser or importer. Each takes (db, upload_id) and
# returns the total/processed/failed counts.
IMPORTERS: dict[ReportType, Callable[..., dict[str, int]]] = {
    ReportType.APR: parse_apr_upload,
    ReportType.SHIFT_ADHERENCE: parse_shift_adherence_upload,
    ReportType.SHRINKAGE: parse_shrinkage_upload,
    ReportType.MASTER_DATABASE: import_master_database,
    ReportType.EMPLOYEE_ROSTER: parse_employee_roster_upload,
    ReportType.DAILY_ACTIVITY: parse_daily_activity_upload,
    ReportType.SHRINKAGE_HOURS: parse_shrinkage_hours_upload,
}


def build_summary(db: Session, upload_id: UUID, counts: dict[str, int]) -> ImportSummary:
    """Add the skipped-row explanation the importer saved on the upload record."""
    upload_history = db.get(UploadHistory, upload_id)
    message = None
    if upload_history is not None:
        db.refresh(upload_history)
        message = upload_history.error_message
    return ImportSummary(**counts, message=message)


@router.post(
    "/master-database/{upload_id}",
    response_model=ImportSummary,
    dependencies=[Depends(require_role(IMPORT_ROLES))],
)
def import_master_database_upload(
    upload_id: UUID,
    db: Session = Depends(get_db),
) -> ImportSummary:
    counts = import_master_database(db=db, upload_id=upload_id)
    return build_summary(db, upload_id, counts)


@router.post(
    "/{report_type}/{upload_id}",
    response_model=ImportSummary,
    dependencies=[Depends(require_role(IMPORT_ROLES))],
)
def import_report_upload(
    report_type: ReportType,
    upload_id: UUID,
    db: Session = Depends(get_db),
) -> ImportSummary:
    importer = IMPORTERS.get(report_type)
    if importer is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Import is not supported yet for {report_type.value} reports",
        )

    upload_history = db.get(UploadHistory, upload_id)
    if upload_history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload history not found",
        )
    if upload_history.report_type != report_type.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload is not a {report_type.value} report",
        )
    if not is_importable(upload_history):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload must be validated before import",
        )

    counts = importer(db=db, upload_id=upload_id)
    return build_summary(db, upload_id, counts)
