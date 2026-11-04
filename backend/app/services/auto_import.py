"""Import an upload automatically as soon as it passes validation."""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.upload_history import UploadHistory
from app.models.user import User, UserRole
from app.parsers.upload_status import mark_upload_failed
from app.reports.report_types import ReportType
from app.services.file_upload import SheetUpload, is_importable


logger = logging.getLogger(__name__)

AUTO_IMPORT_ROLES = (UserRole.ADMIN, UserRole.MIS)
# Employee data goes first so later reports can be matched to employees.
MASTER_FIRST = {
    ReportType.MASTER_DATABASE.value,
    ReportType.EMPLOYEE_ROSTER.value,
}
AUTO_IMPORT_FAILURE_MESSAGE = (
    "Automatic import failed. The file is valid, so use Process report to retry."
)


def can_auto_process(user: User) -> bool:
    return settings.AUTO_PROCESS_UPLOADS and user.role in AUTO_IMPORT_ROLES


def auto_process_sheets(
    db: Session,
    sheets: list[SheetUpload],
    user: User,
) -> set[UUID]:
    """Import every validated sheet. Returns the ids of the uploads it tried.

    Only ADMIN and MIS uploads are imported (the same roles that may press
    "Process report"). A failure on one sheet never stops the others and never
    fails the upload itself: the sheet is marked FAILED and can be retried.
    """
    if not can_auto_process(user):
        return set()

    # Imported here because the importer table lives with the import routes.
    from app.api.routes.imports import IMPORTERS

    ordered = sorted(
        sheets,
        key=lambda sheet: 0 if sheet.upload_history.report_type in MASTER_FIRST else 1,
    )
    attempted: set[UUID] = set()

    for sheet in ordered:
        upload = sheet.upload_history
        upload_id = upload.id
        try:
            importer = IMPORTERS.get(ReportType(upload.report_type))
        except ValueError:
            continue
        if importer is None or not is_importable(upload):
            continue

        attempted.add(upload_id)
        try:
            importer(db=db, upload_id=upload_id)
        except Exception:
            logger.exception("Automatic import failed for upload %s", upload_id)
            db.rollback()
            failed = db.get(UploadHistory, upload_id)
            if failed is not None and failed.upload_status != "FAILED":
                mark_upload_failed(
                    db,
                    upload_history=failed,
                    error_message=AUTO_IMPORT_FAILURE_MESSAGE,
                )
        finally:
            db.refresh(upload)

    return attempted
