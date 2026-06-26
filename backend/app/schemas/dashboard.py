from decimal import Decimal

from pydantic import BaseModel, Field


class DashboardKpis(BaseModel):
    head_count: int = Field(ge=0)
    present_count: int = Field(ge=0)
    late_login_count: int = Field(ge=0)
    early_logout_count: int = Field(ge=0)
    shift_adherence_count: int = Field(ge=0)
    non_adherence_count: int = Field(ge=0)
    planned_shrinkage: Decimal = Field(ge=0)
    unplanned_shrinkage: Decimal = Field(ge=0)
    overall_shrinkage: Decimal = Field(ge=0)
    attrition_count: int = Field(ge=0)
    total_talk_time: Decimal = Field(ge=0)
    total_login_time: Decimal = Field(ge=0)
    total_staff_time: Decimal = Field(ge=0)
    total_downtime: Decimal = Field(ge=0)
    total_idle_time: Decimal = Field(ge=0)
    total_break_time: Decimal = Field(ge=0)
