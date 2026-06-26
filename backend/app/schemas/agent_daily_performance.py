from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentDailyPerformanceBase(BaseModel):
    emp_id: str = Field(min_length=1, max_length=50)
    employee_name: str = Field(min_length=1, max_length=255)
    report_date: date
    campaign: str = Field(min_length=1, max_length=100)
    user_group: str = Field(min_length=1, max_length=100)
    attendance: str = Field(min_length=1, max_length=50)
    login_hours: Decimal = Field(ge=0)
    staff_time: Decimal = Field(ge=0)
    talk_time: Decimal = Field(ge=0)
    break_time: Decimal = Field(ge=0)
    idle_time: Decimal = Field(ge=0)
    productivity_percent: Decimal = Field(ge=0, le=100)
    total_calls: int = Field(ge=0)
    dialer_total_calls: int = Field(ge=0)
    dialflow_total_calls: int = Field(ge=0)
    connected_calls: int = Field(ge=0)
    not_connected_calls: int = Field(ge=0)
    positive_calls: int = Field(ge=0)
    conversion_percent: Decimal = Field(ge=0, le=100)
    tl_remark: str = Field(max_length=500)


class AgentDailyPerformanceCreate(AgentDailyPerformanceBase):
    pass


class AgentDailyPerformanceUpdate(BaseModel):
    emp_id: str | None = Field(default=None, min_length=1, max_length=50)
    employee_name: str | None = Field(default=None, min_length=1, max_length=255)
    report_date: date | None = None
    campaign: str | None = Field(default=None, min_length=1, max_length=100)
    user_group: str | None = Field(default=None, min_length=1, max_length=100)
    attendance: str | None = Field(default=None, min_length=1, max_length=50)
    login_hours: Decimal | None = Field(default=None, ge=0)
    staff_time: Decimal | None = Field(default=None, ge=0)
    talk_time: Decimal | None = Field(default=None, ge=0)
    break_time: Decimal | None = Field(default=None, ge=0)
    idle_time: Decimal | None = Field(default=None, ge=0)
    productivity_percent: Decimal | None = Field(default=None, ge=0, le=100)
    total_calls: int | None = Field(default=None, ge=0)
    dialer_total_calls: int | None = Field(default=None, ge=0)
    dialflow_total_calls: int | None = Field(default=None, ge=0)
    connected_calls: int | None = Field(default=None, ge=0)
    not_connected_calls: int | None = Field(default=None, ge=0)
    positive_calls: int | None = Field(default=None, ge=0)
    conversion_percent: Decimal | None = Field(default=None, ge=0, le=100)
    tl_remark: str | None = Field(default=None, max_length=500)


class AgentDailyPerformanceRead(AgentDailyPerformanceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
