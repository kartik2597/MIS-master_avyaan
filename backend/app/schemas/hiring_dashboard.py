from datetime import date

from pydantic import BaseModel, Field


class ExitReasonCount(BaseModel):
    reason: str
    count: int = Field(ge=0)


class HiringSummary(BaseModel):
    """Joiners, leavers and attrition for the period. Percentages are 0-100."""

    # With no dates asked for, the latest 90 days that have hiring/attrition data.
    date_from: date | None = None
    date_to: date | None = None
    # False when no hiring or exit rows exist for the period ("No data" in the UI).
    has_data: bool = False
    joiners: int = Field(default=0, ge=0)
    leavers: int = Field(default=0, ge=0)
    net_change: int = 0
    # Employees on the master at the start of the period, and that number plus
    # joiners minus leavers. None when the period has no start date.
    opening_headcount: int | None = None
    closing_headcount: int | None = None
    # Leavers as a share of the average of opening and closing headcount.
    # None when there is no start date or no headcount to compare against.
    attrition_percent: float | None = None
    top_exit_reasons: list[ExitReasonCount] = Field(default_factory=list)


class HiringTrendPoint(BaseModel):
    month: str  # YYYY-MM
    joiners: int = Field(ge=0)
    leavers: int = Field(ge=0)


class HiringTrends(BaseModel):
    points: list[HiringTrendPoint] = Field(default_factory=list)
    date_from: date | None = None
    date_to: date | None = None


class HiringTeamRow(BaseModel):
    team: str
    joiners: int = Field(ge=0)
    leavers: int = Field(ge=0)
    net_change: int


class HiringTeamList(BaseModel):
    items: list[HiringTeamRow] = Field(default_factory=list)
    date_from: date | None = None
    date_to: date | None = None


class HiringEventRow(BaseModel):
    emp_id: str
    employee_name: str
    event_type: str  # JOINED or LEFT
    event_date: date
    team: str
    designation: str
    manager_name: str
    # Exit reason for a leaver, hiring source for a joiner. Empty when not given.
    detail: str


class HiringEventList(BaseModel):
    items: list[HiringEventRow] = Field(default_factory=list)
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    date_from: date | None = None
    date_to: date | None = None
