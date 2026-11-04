from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.routes.dashboard import ScopeDep, _check_range
from app.database.session import get_db
from app.schemas.project_dashboard import (
    BenchList,
    ProjectEmployeeList,
    ProjectHoursList,
    ProjectSummary,
    ProjectTrends,
)
from app.services.project_dashboard import (
    get_bench,
    get_project_employees,
    get_project_hours,
    get_project_summary,
    get_project_trends,
)


# Same access rules as the agent dashboard: ADMIN and MIS see everyone, MANAGER and
# TL see their own team (ScopeDep also applies the process / manager / TL filters).
router = APIRouter()


@router.get("/summary", response_model=ProjectSummary)
def read_project_summary(
    scope: ScopeDep,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
) -> ProjectSummary:
    _check_range(date_from, date_to)
    return get_project_summary(db, date_from=date_from, date_to=date_to, scope=scope)


@router.get("/projects", response_model=ProjectHoursList)
def read_project_hours(
    scope: ScopeDep,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    db: Session = Depends(get_db),
) -> ProjectHoursList:
    _check_range(date_from, date_to)
    return get_project_hours(
        db, date_from=date_from, date_to=date_to, scope=scope, limit=limit
    )


@router.get("/employees", response_model=ProjectEmployeeList)
def read_project_employees(
    scope: ScopeDep,
    date_from: date | None = None,
    date_to: date | None = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
    db: Session = Depends(get_db),
) -> ProjectEmployeeList:
    _check_range(date_from, date_to)
    return get_project_employees(
        db,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=page,
        page_size=page_size,
        scope=scope,
    )


@router.get("/bench", response_model=BenchList)
def read_bench(
    scope: ScopeDep,
    date_from: date | None = None,
    date_to: date | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
    db: Session = Depends(get_db),
) -> BenchList:
    _check_range(date_from, date_to)
    return get_bench(
        db,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        scope=scope,
    )


@router.get("/trends", response_model=ProjectTrends)
def read_project_trends(
    scope: ScopeDep,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
) -> ProjectTrends:
    _check_range(date_from, date_to)
    return get_project_trends(db, date_from=date_from, date_to=date_to, scope=scope)
