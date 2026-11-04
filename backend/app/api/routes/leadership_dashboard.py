from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.routes.dashboard import ScopeDep, _check_range
from app.database.session import get_db
from app.schemas.leadership_dashboard import LeadershipSummary
from app.services.leadership_dashboard import get_leadership_summary


# Same access rules as the other dashboards: ADMIN and MIS see everyone, MANAGER and
# TL see their own team (ScopeDep also applies the process / manager / TL filters).
router = APIRouter()


@router.get("/summary", response_model=LeadershipSummary)
def read_leadership_summary(
    scope: ScopeDep,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
) -> LeadershipSummary:
    _check_range(date_from, date_to)
    return get_leadership_summary(db, date_from=date_from, date_to=date_to, scope=scope)
