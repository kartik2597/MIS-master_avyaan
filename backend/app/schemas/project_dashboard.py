from datetime import date

from pydantic import BaseModel, Field


class ProjectSummary(BaseModel):
    """Headline numbers for the period. Hours are real hours, percentages are 0-100."""

    # The period the numbers describe. With no dates asked for, it is the latest
    # 30 days that have timesheet data.
    date_from: date | None = None
    date_to: date | None = None
    # False when there are no timesheet rows for the period, so the UI can say
    # "No data" instead of showing zeros that look real.
    has_data: bool = False
    total_hours: float = Field(default=0, ge=0)
    billable_hours: float = Field(default=0, ge=0)
    non_billable_hours: float = Field(default=0, ge=0)
    # Billable hours as a share of all logged hours. None when nothing was logged.
    billable_percent: float | None = None
    employees_logged: int = Field(default=0, ge=0)
    active_projects: int = Field(default=0, ge=0)
    avg_hours_per_employee: float = Field(default=0, ge=0)


class ProjectHoursRow(BaseModel):
    project_name: str
    client_name: str
    total_hours: float = Field(ge=0)
    billable_hours: float = Field(ge=0)
    employees: int = Field(ge=0)
    # This project's share of all hours in the period.
    share_percent: float = Field(ge=0)


class ProjectHoursList(BaseModel):
    items: list[ProjectHoursRow] = Field(default_factory=list)
    date_from: date | None = None
    date_to: date | None = None


class ProjectEmployeeRow(BaseModel):
    emp_id: str
    employee_name: str
    total_hours: float = Field(ge=0)
    billable_hours: float = Field(ge=0)
    billable_percent: float | None = None
    projects: int = Field(ge=0)
    days_logged: int = Field(ge=0)


class ProjectEmployeeList(BaseModel):
    items: list[ProjectEmployeeRow] = Field(default_factory=list)
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    date_from: date | None = None
    date_to: date | None = None


class BenchEmployeeRow(BaseModel):
    emp_id: str
    employee_name: str
    process: str
    designation: str
    manager_name: str
    tl_name: str


class BenchList(BaseModel):
    """Active employees who logged no project hours in the period."""

    items: list[BenchEmployeeRow] = Field(default_factory=list)
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    date_from: date | None = None
    date_to: date | None = None


class ProjectTrendPoint(BaseModel):
    report_date: date
    total_hours: float = Field(ge=0)
    billable_hours: float = Field(ge=0)


class ProjectTrends(BaseModel):
    points: list[ProjectTrendPoint] = Field(default_factory=list)
    date_from: date | None = None
    date_to: date | None = None
