from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UploadHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_name: str
    original_file_name: str
    report_type: str
    file_size: int
    uploaded_by: UUID
    upload_status: str
    total_records: int
    processed_records: int
    failed_records: int
    error_message: str | None
    validation_result: dict[str, Any] | None
    uploaded_at: datetime
    processing_started_at: datetime | None
    processing_completed_at: datetime | None


class UploadHistoryList(BaseModel):
    items: list[UploadHistoryRead]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class FileUploadDetectionResponse(BaseModel):
    upload_id: UUID
    file_name: str
    detected_report_type: str | None
    confidence_score: int = Field(ge=0, le=100)
    total_columns: int = Field(ge=0)
    missing_columns: list[str]
