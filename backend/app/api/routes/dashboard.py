from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.database.session import get_db
from app.models.user import UserRole
from app.schemas.dashboard import DashboardKpis
from app.services.dashboard import get_dashboard_kpis


router = APIRouter()

VIEW_ROLES = [UserRole.ADMIN, UserRole.MIS, UserRole.MANAGER, UserRole.TL]


@router.get(
    "/kpis",
    response_model=DashboardKpis,
    dependencies=[Depends(require_role(VIEW_ROLES))],
)
def read_dashboard_kpis(db: Session = Depends(get_db)) -> DashboardKpis:
    return get_dashboard_kpis(db=db)
