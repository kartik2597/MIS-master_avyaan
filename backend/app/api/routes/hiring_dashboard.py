from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.routes.dashboard import ScopeDep, _check_range
from app.database.session import get_db
from app.schemas.hiring_dashboard import (
    HiringEventList,
    HiringSummary,
    HiringTeamList,
    HiringTrends,
)
from app.services.hiring_dashboard import (
    get_hiring_events,
    get_hiring_summary,
    get_hiring_teams,
    get_hiring_trends,
)


# Same access rules as the agent dashboard: ADMIN and MIS see everyone, MANAGER and
# TL see their own team (ScopeDep also applies the process / manager / TL filters).
router = APIRouter()


@router.get("/summary", response_model=HiringSummary)
def read_hiring_summary(
    scope: ScopeDep,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
) -> HiringSummary:
    _check_range(date_from, date_to)
    return get_hiring_summary(db, date_from=date_from, date_to=date_to, scope=scope)


@router.get("/trends", response_model=HiringTrends)
def read_hiring_trends(
    scope: ScopeDep,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
) -> HiringTrends:
    _check_range(date_from, date_to)
    return get_hiring_trends(db, date_from=date_from, date_to=date_to, scope=scope)


@router.get("/teams", response_model=HiringTeamList)
def read_hiring_teams(
    scope: ScopeDep,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
) -> HiringTeamList:
    _check_range(date_from, date_to)
    return get_hiring_teams(db, date_from=date_from, date_to=date_to, scope=scope)


@router.get("/events", response_model=HiringEventList)
def read_hiring_events(
    scope: ScopeDep,
    date_from: date | None = None,
    date_to: date | None = None,
    event_type: Literal["JOINED", "LEFT"] | None = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
    db: Session = Depends(get_db),
) -> HiringEventList:
    _check_range(date_from, date_to)
    return get_hiring_events(
        db,
        date_from=date_from,
        date_to=date_to,
        event_type=event_type,
        search=search,
        page=page,
        page_size=page_size,
        scope=scope,
    )
