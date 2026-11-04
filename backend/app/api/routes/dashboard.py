from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.database.session import get_db
from app.models.user import User, UserRole
from app.schemas.dashboard import (
    AttendanceBreakdown,
    DashboardAgentList,
    DashboardFilterOptions,
    DashboardKpis,
    DashboardTrends,
)
from app.services.dashboard import (
    apply_dashboard_filters,
    get_dashboard_agents,
    get_dashboard_attendance,
    get_dashboard_filter_options,
    get_dashboard_kpis,
    get_dashboard_scope,
    get_dashboard_trends,
)


router = APIRouter()

VIEW_ROLES = [UserRole.ADMIN, UserRole.MIS, UserRole.MANAGER, UserRole.TL]

# Every dashboard endpoint depends on this, so it knows who is asking. ADMIN and
# MIS see everyone; MANAGER and TL see only their own team (get_dashboard_scope).
ViewerDep = Annotated[User, Depends(require_role(VIEW_ROLES))]


def get_filtered_scope(
    viewer: ViewerDep,
    db: Session = Depends(get_db),
    process: Annotated[str | None, Query(max_length=100)] = None,
    manager: Annotated[str | None, Query(max_length=255)] = None,
    tl: Annotated[str | None, Query(max_length=255)] = None,
    emp_id: Annotated[str | None, Query(max_length=50)] = None,
) -> Select | None:
    """The viewer's team scope, narrowed by the optional dashboard filters.

    Filters only shrink the scope, so a MANAGER or TL can never use them to see
    employees outside their own team.
    """
    return apply_dashboard_filters(
        get_dashboard_scope(db, viewer),
        process=process,
        manager=manager,
        tl=tl,
        emp_id=emp_id,
    )


ScopeDep = Annotated[Select | None, Depends(get_filtered_scope)]


def _check_range(date_from: date | None, date_to: date | None) -> None:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be on or before date_to",
        )


@router.get("/filters", response_model=DashboardFilterOptions)
def read_dashboard_filters(
    viewer: ViewerDep,
    db: Session = Depends(get_db),
) -> DashboardFilterOptions:
    """Values for the process / manager / TL drop-downs, limited to the viewer's team."""
    return get_dashboard_filter_options(db=db, scope=get_dashboard_scope(db, viewer))


@router.get("/kpis", response_model=DashboardKpis)
def read_dashboard_kpis(
    scope: ScopeDep,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
) -> DashboardKpis:
    _check_range(date_from, date_to)
    return get_dashboard_kpis(
        db=db,
        date_from=date_from,
        date_to=date_to,
        scope=scope,
    )


@router.get("/trends", response_model=DashboardTrends)
def read_dashboard_trends(
    scope: ScopeDep,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
) -> DashboardTrends:
    _check_range(date_from, date_to)
    return get_dashboard_trends(
        db=db,
        date_from=date_from,
        date_to=date_to,
        scope=scope,
    )


@router.get("/attendance", response_model=AttendanceBreakdown)
def read_dashboard_attendance(
    scope: ScopeDep,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
) -> AttendanceBreakdown:
    _check_range(date_from, date_to)
    return get_dashboard_attendance(
        db=db,
        date_from=date_from,
        date_to=date_to,
        scope=scope,
    )


@router.get("/agents", response_model=DashboardAgentList)
def read_dashboard_agents(
    scope: ScopeDep,
    date_from: date | None = None,
    date_to: date | None = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
    db: Session = Depends(get_db),
) -> DashboardAgentList:
    _check_range(date_from, date_to)
    return get_dashboard_agents(
        db=db,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=page,
        page_size=page_size,
        scope=scope,
    )
