from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentShrinkageBase(BaseModel):
    emp_id: str = Field(min_length=1, max_length=50)
    employee_name: str = Field(min_length=1, max_length=255)
    report_date: date
    status: str = Field(min_length=1, max_length=50)
    process: str = Field(min_length=1, max_length=100)
    designation: str = Field(min_length=1, max_length=100)
    manager_name: str = Field(min_length=1, max_length=255)
    date_of_joining: date
    login_hours_seconds: int = Field(ge=0)
    attendance: str = Field(min_length=1, max_length=50)
    employee_age_days: int = Field(ge=0)
    tenure_bucket: str = Field(min_length=1, max_length=50)
    agent_count: int = Field(ge=0)
    present_count: int = Field(ge=0)
    absent_count: int = Field(ge=0)
    lwp_count: int = Field(ge=0)
    cl_count: int = Field(ge=0)
    half_day_count: int = Field(ge=0)
    training_count: int = Field(ge=0)
    planned_shrinkage: Decimal = Field(ge=0)
    unplanned_shrinkage: Decimal = Field(ge=0)
    opening_headcount: int = Field(ge=0)
    closing_headcount: int = Field(ge=0)
    attrition: int = Field(ge=0)


class AgentShrinkageCreate(AgentShrinkageBase):
    pass


class AgentShrinkageUpdate(BaseModel):
    emp_id: str | None = Field(default=None, min_length=1, max_length=50)
    employee_name: str | None = Field(default=None, min_length=1, max_length=255)
    report_date: date | None = None
    status: str | None = Field(default=None, min_length=1, max_length=50)
    process: str | None = Field(default=None, min_length=1, max_length=100)
    designation: str | None = Field(default=None, min_length=1, max_length=100)
    manager_name: str | None = Field(default=None, min_length=1, max_length=255)
    date_of_joining: date | None = None
    login_hours_seconds: int | None = Field(default=None, ge=0)
    attendance: str | None = Field(default=None, min_length=1, max_length=50)
    employee_age_days: int | None = Field(default=None, ge=0)
    tenure_bucket: str | None = Field(default=None, min_length=1, max_length=50)
    agent_count: int | None = Field(default=None, ge=0)
    present_count: int | None = Field(default=None, ge=0)
    absent_count: int | None = Field(default=None, ge=0)
    lwp_count: int | None = Field(default=None, ge=0)
    cl_count: int | None = Field(default=None, ge=0)
    half_day_count: int | None = Field(default=None, ge=0)
    training_count: int | None = Field(default=None, ge=0)
    planned_shrinkage: Decimal | None = Field(default=None, ge=0)
    unplanned_shrinkage: Decimal | None = Field(default=None, ge=0)
    opening_headcount: int | None = Field(default=None, ge=0)
    closing_headcount: int | None = Field(default=None, ge=0)
    attrition: int | None = Field(default=None, ge=0)


class AgentShrinkageRead(AgentShrinkageBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
