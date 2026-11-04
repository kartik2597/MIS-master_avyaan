import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class UploadHistory(Base):
    __tablename__ = "upload_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # SHA-256 of the stored file, used to catch the same file being uploaded twice.
    # Null for uploads made before duplicate detection existed.
    file_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    upload_status: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    total_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Rows an import skipped, as [{"row": 12, "reason": "..."}]. Capped (see
    # MAX_STORED_ROW_ERRORS), so failed_records can be larger than this list.
    row_errors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    processing_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    uploader = relationship("User")

    @property
    def uploaded_by_name(self) -> str | None:
        """The uploader's name, so the UI can show a person instead of a UUID."""
        return self.uploader.full_name if self.uploader is not None else None
