from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole


def _clean_emp_id(value: str | None) -> str | None:
    """Trim the Employee ID; an empty value means 'not linked'."""
    if value is None:
        return None
    value = value.strip()
    return value or None


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    is_active: bool = True
    emp_id: str | None = Field(default=None, max_length=50)

    _trim_emp_id = field_validator("emp_id")(_clean_emp_id)


class UserEmployeeLink(BaseModel):
    """Set (or clear, with null) the employee a user belongs to."""

    emp_id: str | None = Field(default=None, max_length=50)

    _trim_emp_id = field_validator("emp_id")(_clean_emp_id)


class UserUpdate(BaseModel):
    """An admin's edit of a user. Only the fields that are sent are changed.

    `emp_id` may be null to clear the link. The other fields are left alone when
    they are missing or null. A `password` here is an admin reset.
    """

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None
    is_active: bool | None = None
    emp_id: str | None = Field(default=None, max_length=50)
    password: str | None = Field(default=None, min_length=8, max_length=128)

    _trim_emp_id = field_validator("emp_id")(_clean_emp_id)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    emp_id: str | None = None
    created_at: datetime
    updated_at: datetime
