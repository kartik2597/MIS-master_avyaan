from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.database.session import get_db
from app.imports import import_master_database
from app.models.user import UserRole
from app.schemas.imports import ImportSummary


router = APIRouter()

IMPORT_ROLES = [UserRole.ADMIN, UserRole.MIS]


@router.post(
    "/master-database/{upload_id}",
    response_model=ImportSummary,
    dependencies=[Depends(require_role(IMPORT_ROLES))],
)
def import_master_database_upload(
    upload_id: UUID,
    db: Session = Depends(get_db),
) -> ImportSummary:
    return ImportSummary(**import_master_database(db=db, upload_id=upload_id))

