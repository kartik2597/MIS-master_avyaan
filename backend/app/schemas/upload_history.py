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
    uploaded_by_name: str | None = None
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


class UploadSummary(BaseModel):
    """Counts over every upload the viewer may see (not just one page)."""

    total: int = Field(ge=0)
    completed: int = Field(ge=0)
    # Uploads whose status is FAILED or VALIDATION_FAILED.
    failed: int = Field(ge=0)
    processing: int = Field(ge=0)
    # Failed uploads plus uploads where some rows were skipped.
    with_issues: int = Field(ge=0)
    # The same, for uploads made in the last 7 days (drives the sidebar badge).
    recent_issues: int = Field(ge=0)


class SheetUploadResult(BaseModel):
    """One report found in the uploaded file (a sheet of a workbook, or a CSV)."""

    upload_id: UUID
    sheet_name: str | None
    detected_report_type: str | None
    confidence_score: int = Field(ge=0, le=100)
    total_columns: int = Field(ge=0)
    total_records: int = Field(ge=0)
    missing_columns: list[str]


class FileUploadDetectionResponse(BaseModel):
    # The first report found in the file (kept so single-report clients still work).
    upload_id: UUID
    file_name: str
    detected_report_type: str | None
    confidence_score: int = Field(ge=0, le=100)
    total_columns: int = Field(ge=0)
    missing_columns: list[str]
    # Every report found in the file, and the sheets that were skipped.
    sheets: list[SheetUploadResult] = Field(default_factory=list)
    ignored_sheets: list[str] = Field(default_factory=list)


class RowErrorItem(BaseModel):
    """One row an import skipped. Row 0 means the problem is about the file as a whole."""

    row: int = Field(ge=0)
    reason: str


class UploadValidationReport(BaseModel):
    """Everything that went wrong with one upload: columns first, then skipped rows."""

    upload_id: UUID
    original_file_name: str
    report_type: str
    upload_status: str
    uploaded_by_name: str | None = None
    uploaded_at: datetime
    sheet_name: str | None = None
    # None when the upload has no validation result yet.
    columns_valid: bool | None = None
    validation_score: float | None = None
    missing_columns: list[str] = Field(default_factory=list)
    extra_columns: list[str] = Field(default_factory=list)
    total_records: int = Field(ge=0)
    processed_records: int = Field(ge=0)
    failed_records: int = Field(ge=0)
    # The short summary saved on the upload (also holds the reason a whole import failed).
    error_message: str | None = None
    row_errors: list[RowErrorItem] = Field(default_factory=list)
    # True when more rows failed than are listed (the stored list is capped).
    row_errors_truncated: bool = False
