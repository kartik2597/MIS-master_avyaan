import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    emp_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    employee_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    mobile: Mapped[str] = mapped_column(String(30), nullable=False)
    department: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    process: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    designation: Mapped[str] = mapped_column(String(100), nullable=False)
    manager_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    tl_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    date_of_joining: Mapped[date] = mapped_column(Date, nullable=False)
    employment_status: Mapped[str] = mapped_column(String(50), nullable=False)
    location: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

