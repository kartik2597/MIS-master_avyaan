import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ProjectTimesheet(Base):
    """Hours one employee logged against one project (and task) on one day."""

    __tablename__ = "project_timesheets"
    __table_args__ = (
        UniqueConstraint(
            "emp_id",
            "report_date",
            "project_name",
            "task_type",
            name="uq_project_timesheets_entry",
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
    # Named report_date like the other report tables, so the shared row checks
    # (date far in the past or future) and the dashboards treat it the same way.
    report_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    project_name: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    client_name: Mapped[str] = mapped_column(String(150), nullable=False)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    billable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
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
