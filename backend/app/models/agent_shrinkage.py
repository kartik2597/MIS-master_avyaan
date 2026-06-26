import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AgentShrinkage(Base):
    __tablename__ = "agent_shrinkage"
    __table_args__ = (
        UniqueConstraint(
            "emp_id",
            "report_date",
            name="uq_agent_shrinkage_emp_report_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    emp_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    employee_name: Mapped[str] = mapped_column(String(255), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    process: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    designation: Mapped[str] = mapped_column(String(100), nullable=False)
    manager_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    date_of_joining: Mapped[date] = mapped_column(Date, nullable=False)
    login_hours_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    attendance: Mapped[str] = mapped_column(String(50), nullable=False)
    employee_age_days: Mapped[int] = mapped_column(Integer, nullable=False)
    tenure_bucket: Mapped[str] = mapped_column(String(50), nullable=False)
    agent_count: Mapped[int] = mapped_column(Integer, nullable=False)
    present_count: Mapped[int] = mapped_column(Integer, nullable=False)
    absent_count: Mapped[int] = mapped_column(Integer, nullable=False)
    lwp_count: Mapped[int] = mapped_column(Integer, nullable=False)
    cl_count: Mapped[int] = mapped_column(Integer, nullable=False)
    half_day_count: Mapped[int] = mapped_column(Integer, nullable=False)
    training_count: Mapped[int] = mapped_column(Integer, nullable=False)
    planned_shrinkage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    unplanned_shrinkage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    opening_headcount: Mapped[int] = mapped_column(Integer, nullable=False)
    closing_headcount: Mapped[int] = mapped_column(Integer, nullable=False)
    attrition: Mapped[int] = mapped_column(Integer, nullable=False)
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
