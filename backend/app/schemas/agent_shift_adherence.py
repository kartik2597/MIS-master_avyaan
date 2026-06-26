from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentShiftAdherenceBase(BaseModel):
    emp_id: str = Field(min_length=1, max_length=50)
    employee_name: str = Field(min_length=1, max_length=255)
    report_date: date
    status: str = Field(max_length=50)
    process: str = Field(min_length=1, max_length=100)
    designation: str = Field(min_length=1, max_length=100)
    manager_name: str = Field(min_length=1, max_length=255)
    attendance: str = Field(min_length=1, max_length=50)
    shift_start_time: time
    shift_end_time: time
    actual_login_time: time
    actual_logout_time: time
    login_hours_seconds: int = Field(ge=0)
    downtime_seconds: int = Field(ge=0)
    login_plus_downtime_seconds: int = Field(ge=0)
    shift_login_adherence_percent: Decimal = Field(ge=0, le=100)
    adherence_status: str = Field(min_length=1, max_length=50)
    late_login_minutes: int = Field(ge=0)
    early_logout_minutes: int = Field(ge=0)
    adherence_flag: bool
    non_adherence_flag: bool
    non_adherence_percent: Decimal = Field(ge=0, le=100)


class AgentShiftAdherenceCreate(AgentShiftAdherenceBase):
    pass


class AgentShiftAdherenceUpdate(BaseModel):
    emp_id: str | None = Field(default=None, min_length=1, max_length=50)
    employee_name: str | None = Field(default=None, min_length=1, max_length=255)
    report_date: date | None = None
    status: str | None = Field(default=None, max_length=50)
    process: str | None = Field(default=None, min_length=1, max_length=100)
    designation: str | None = Field(default=None, min_length=1, max_length=100)
    manager_name: str | None = Field(default=None, min_length=1, max_length=255)
    attendance: str | None = Field(default=None, min_length=1, max_length=50)
    shift_start_time: time | None = None
    shift_end_time: time | None = None
    actual_login_time: time | None = None
    actual_logout_time: time | None = None
    login_hours_seconds: int | None = Field(default=None, ge=0)
    downtime_seconds: int | None = Field(default=None, ge=0)
    login_plus_downtime_seconds: int | None = Field(default=None, ge=0)
    shift_login_adherence_percent: Decimal | None = Field(default=None, ge=0, le=100)
    adherence_status: str | None = Field(default=None, min_length=1, max_length=50)
    late_login_minutes: int | None = Field(default=None, ge=0)
    early_logout_minutes: int | None = Field(default=None, ge=0)
    adherence_flag: bool | None = None
    non_adherence_flag: bool | None = None
    non_adherence_percent: Decimal | None = Field(default=None, ge=0, le=100)


class AgentShiftAdherenceRead(AgentShiftAdherenceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
