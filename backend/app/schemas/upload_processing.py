from pydantic import Field

from app.schemas.upload_history import FileUploadDetectionResponse, SheetUploadResult


class ProcessedSheetResult(SheetUploadResult):
    """A detected sheet plus what happened to it after upload.

    With automatic processing on, a valid sheet is imported straight away, so the
    status is already COMPLETED (or FAILED) when the upload call returns.
    """

    upload_status: str
    processed_records: int = Field(default=0, ge=0)
    failed_records: int = Field(default=0, ge=0)
    error_message: str | None = None
    # True when the server tried to import this sheet without a manual step.
    auto_processed: bool = False


class FileUploadProcessingResponse(FileUploadDetectionResponse):
    sheets: list[ProcessedSheetResult] = Field(default_factory=list)
    auto_processed: bool = False
