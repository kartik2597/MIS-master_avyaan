import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AgentShiftAdherence(Base):
    __tablename__ = "agent_shift_adherence"
    __table_args__ = (
        UniqueConstraint(
            "emp_id",
            "report_date",
            name="uq_agent_shift_adherence_emp_report_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # The upload that last wrote this row. Deleting that upload deletes the row.
    upload_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("upload_history.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    emp_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    employee_name: Mapped[str] = mapped_column(String(255), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    process: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    designation: Mapped[str] = mapped_column(String(100), nullable=False)
    manager_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    attendance: Mapped[str] = mapped_column(String(50), nullable=False)
    shift_start_time: Mapped[time] = mapped_column(Time, nullable=False)
    shift_end_time: Mapped[time] = mapped_column(Time, nullable=False)
    actual_login_time: Mapped[time] = mapped_column(Time, nullable=False)
    actual_logout_time: Mapped[time] = mapped_column(Time, nullable=False)
    login_hours_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    downtime_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    login_plus_downtime_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    shift_login_adherence_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    adherence_status: Mapped[str] = mapped_column(String(50), nullable=False)
    late_login_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    early_logout_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    adherence_flag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    non_adherence_flag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    non_adherence_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
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
