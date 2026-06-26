from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EmployeeBase(BaseModel):
    emp_id: str = Field(min_length=1, max_length=50)
    employee_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    mobile: str = Field(min_length=1, max_length=30)
    department: str = Field(min_length=1, max_length=100)
    process: str = Field(min_length=1, max_length=100)
    designation: str = Field(min_length=1, max_length=100)
    manager_name: str = Field(min_length=1, max_length=255)
    tl_name: str = Field(min_length=1, max_length=255)
    date_of_joining: date
    employment_status: str = Field(min_length=1, max_length=50)
    location: str = Field(min_length=1, max_length=100)


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    emp_id: str | None = Field(default=None, min_length=1, max_length=50)
    employee_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    mobile: str | None = Field(default=None, min_length=1, max_length=30)
    department: str | None = Field(default=None, min_length=1, max_length=100)
    process: str | None = Field(default=None, min_length=1, max_length=100)
    designation: str | None = Field(default=None, min_length=1, max_length=100)
    manager_name: str | None = Field(default=None, min_length=1, max_length=255)
    tl_name: str | None = Field(default=None, min_length=1, max_length=255)
    date_of_joining: date | None = None
    employment_status: str | None = Field(default=None, min_length=1, max_length=50)
    location: str | None = Field(default=None, min_length=1, max_length=100)


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class EmployeeList(BaseModel):
    items: list[EmployeeRead]
    total: int
    page: int
    page_size: int

