import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

EVENT_JOINED = "JOINED"
EVENT_LEFT = "LEFT"


class EmployeeMovement(Base):
    """One hiring (JOINED) or exit (LEFT) event for an employee."""

    __tablename__ = "employee_movements"
    __table_args__ = (
        UniqueConstraint(
            "emp_id",
            "event_type",
            "report_date",
            name="uq_employee_movements_event",
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
    # JOINED or LEFT (see EVENT_JOINED / EVENT_LEFT).
    event_type: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    # The joining date, or the last working day. Named report_date like the other
    # report tables so the shared row checks apply to it.
    report_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    team: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    designation: Mapped[str] = mapped_column(String(100), nullable=False)
    manager_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Why the person left (empty for a joiner).
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    # Where the hire came from, e.g. Referral or Campus (empty for a leaver).
    hiring_source: Mapped[str] = mapped_column(String(150), nullable=False)
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
