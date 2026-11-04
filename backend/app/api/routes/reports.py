from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.routes.dashboard import ScopeDep, ViewerDep, _check_range
from app.database.session import get_db
from app.services.report_export import (
    CONTENT_TYPES,
    REPORT_KINDS,
    REPORT_SECTIONS,
    build_report_data,
    period_for,
    render_report,
)


# Same access rules as the dashboards: ADMIN and MIS get everyone, MANAGER and TL get
# their own team (ScopeDep also applies the process / manager / TL filters), so a
# downloaded report always matches what the person sees on screen.
router = APIRouter()

Kind = Literal["daily", "weekly", "monthly"]
FileFormat = Literal["xlsx", "pdf"]
Section = Literal["agent", "project", "hiring", "uploads", "utilization"]


@router.get("/periods")
def read_report_periods(_viewer: ViewerDep) -> dict[str, dict[str, date]]:
    """The finished period each report kind covers by default (yesterday, last week, last month).

    Needs a signed-in user with a dashboard role, like every other report endpoint.
    """
    today = date.today()
    periods = {}
    for kind in REPORT_KINDS:
        start, end = period_for(kind, today)
        periods[kind] = {"date_from": start, "date_to": end}
    return periods


@router.get("/{kind}")
def download_report(
    kind: Kind,
    scope: ScopeDep,
    date_from: date | None = None,
    date_to: date | None = None,
    file_format: Annotated[FileFormat, Query(alias="format")] = "xlsx",
    sections: Annotated[list[Section] | None, Query()] = None,
    db: Session = Depends(get_db),
) -> Response:
    """Build a daily, weekly or monthly report and return it as an Excel or PDF file.

    Give both dates or neither. With neither, the report covers the latest finished
    period of that kind. `sections` picks what goes in (agent, project, hiring,
    uploads, utilization); leave it out for all of them. The uploads section is only filled for
    ADMIN and MIS, because uploads do not belong to a team.
    """
    if (date_from is None) != (date_to is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Give both date_from and date_to, or neither.",
        )
    _check_range(date_from, date_to)
    if date_from is None or date_to is None:
        date_from, date_to = period_for(kind, date.today())

    chosen = list(dict.fromkeys(sections)) if sections else list(REPORT_SECTIONS)
    data = build_report_data(db, kind, date_from, date_to, scope=scope, sections=chosen)
    content = render_report(data, file_format)
    return Response(
        content=content,
        media_type=CONTENT_TYPES[file_format],
        headers={"Content-Disposition": f'attachment; filename="{data.file_stem}.{file_format}"'},
    )
