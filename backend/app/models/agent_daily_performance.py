import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AgentDailyPerformance(Base):
    __tablename__ = "agent_daily_performance"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    emp_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    employee_name: Mapped[str] = mapped_column(String(255), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    campaign: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    user_group: Mapped[str] = mapped_column(String(100), nullable=False)
    attendance: Mapped[str] = mapped_column(String(50), nullable=False)
    login_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    staff_time: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    talk_time: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    break_time: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    idle_time: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    productivity_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    total_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    dialer_total_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    dialflow_total_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    connected_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    not_connected_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    positive_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    conversion_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    tl_remark: Mapped[str] = mapped_column(String(500), nullable=False)
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
